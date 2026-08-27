"""Read immutable manuscript files without external conversion processes."""

from __future__ import annotations

import hashlib
import io
import os
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_TEXT_CHARS = 300_000
DEFAULT_MIN_TEXT_CHARS = 1_000
SUPPORTED_SUFFIXES = frozenset({".txt", ".md", ".markdown", ".rst", ".html", ".htm", ".docx", ".pdf"})
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentReadError(ValueError):
    """Raised when a manuscript cannot be read completely and safely."""


@dataclass(frozen=True, slots=True)
class DocumentContent:
    path: Path
    text: str
    artifact_sha256: str
    semantic_content_sha256: str
    character_count: int
    critical_basis_available: bool
    submission_hold_codes: tuple[str, ...]


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise DocumentReadError(f"{name} must be an integer") from exc
    if value <= 0:
        raise DocumentReadError(f"{name} must be positive")
    return value


def _decode_text(data: bytes) -> str:
    encodings = ("utf-8-sig", "utf-16", "gb18030")
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentReadError("text file is not valid UTF-8, UTF-16, or GB18030")


def _xml_text(data: bytes) -> str:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise DocumentReadError("DOCX contains malformed Word XML") from exc
    parts: list[str] = []
    for element in root.iter():
        if element.tag == WORD_NS + "t" and element.text:
            parts.append(element.text)
        elif element.tag == WORD_NS + "tab":
            parts.append("\t")
        elif element.tag in {WORD_NS + "br", WORD_NS + "cr"}:
            parts.append("\n")
        elif element.tag == WORD_NS + "p":
            parts.append("\n")
    return "".join(parts)


def _read_docx(data: bytes) -> tuple[str, tuple[str, ...]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise DocumentReadError("file is not a valid DOCX archive") from exc
    names = set(archive.namelist())
    if "word/document.xml" not in names:
        raise DocumentReadError("DOCX is missing word/document.xml")
    sections = [("MAIN DOCUMENT", _xml_text(archive.read("word/document.xml")))]
    for name, label in (
        ("word/footnotes.xml", "FOOTNOTES"),
        ("word/endnotes.xml", "ENDNOTES"),
    ):
        if name in names:
            sections.append((label, _xml_text(archive.read(name))))
    holds: list[str] = []
    document_xml = archive.read("word/document.xml")
    if "word/comments.xml" in names or b"<w:ins" in document_xml or b"<w:del" in document_xml:
        holds.append("COMMENTS_OR_TRACKING_REMAIN")
    text = "\n\n".join(f"--- {label} ---\n{content}" for label, content in sections)
    return text, tuple(holds)


def _read_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentReadError("PDF support is unavailable in this build") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise DocumentReadError("PDF text extraction failed") from exc
    return "\n\n".join(f"--- PAGE {index} ---\n{text}" for index, text in enumerate(pages, 1))


def _read_html(data: bytes) -> str:
    parser = _TextHTMLParser()
    parser.feed(_decode_text(data))
    parser.close()
    return "".join(parser.parts)


def normalize_semantic_text(text: str) -> str:
    """Canonicalize visible text for a stable semantic-content receipt hash."""

    normalized = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
    return normalized.strip() + "\n"


def read_document(path: str | Path) -> DocumentContent:
    source = Path(path).expanduser().resolve(strict=True)
    if not source.is_file():
        raise DocumentReadError("manuscript path is not a file")
    suffix = source.suffix.casefold()
    if suffix not in SUPPORTED_SUFFIXES:
        raise DocumentReadError("unsupported manuscript type; use TXT, Markdown, HTML, DOCX, or text-layer PDF")
    max_bytes = _env_int("MRC_MAX_FILE_BYTES", DEFAULT_MAX_FILE_BYTES)
    if source.stat().st_size > max_bytes:
        raise DocumentReadError("manuscript exceeds MRC_MAX_FILE_BYTES; input was not truncated")
    data = source.read_bytes()
    artifact_hash = hashlib.sha256(data).hexdigest()
    holds: tuple[str, ...] = ()
    if suffix == ".docx":
        text, holds = _read_docx(data)
    elif suffix == ".pdf":
        text = _read_pdf(data)
    elif suffix in {".html", ".htm"}:
        text = _read_html(data)
    else:
        text = _decode_text(data)
    semantic_text = normalize_semantic_text(text)
    max_chars = _env_int("MRC_MAX_TEXT_CHARS", DEFAULT_MAX_TEXT_CHARS)
    if len(semantic_text) > max_chars:
        raise DocumentReadError("extracted manuscript exceeds MRC_MAX_TEXT_CHARS; input was not truncated")
    min_chars = _env_int("MRC_MIN_TEXT_CHARS", DEFAULT_MIN_TEXT_CHARS)
    critical_basis = len(semantic_text.strip()) >= min_chars
    semantic_hash = hashlib.sha256(semantic_text.encode("utf-8")).hexdigest()
    return DocumentContent(
        path=source,
        text=semantic_text,
        artifact_sha256=artifact_hash,
        semantic_content_sha256=semantic_hash,
        character_count=len(semantic_text),
        critical_basis_available=critical_basis,
        submission_hold_codes=holds,
    )
