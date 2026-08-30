from __future__ import annotations

import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseDocumentationTests(unittest.TestCase):
    def test_language_entrypoints_are_separate_and_reciprocal(self) -> None:
        readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
        english_body = readme_en.replace("[中文说明](README.zh-CN.md)", "")
        self.assertIsNone(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", english_body))
        self.assertIsNotNone(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", readme_zh))
        self.assertIn("[中文说明](README.zh-CN.md)", readme_en)
        self.assertIn("[English](README.md)", readme_zh)

    def test_public_guides_have_language_pairs(self) -> None:
        guide_roots = {
            "CHANGELOG": ROOT / "docs",
            "CONTRIBUTING": ROOT / ".github",
            "ILLUSTRATIONS": ROOT / "docs",
            "PROVENANCE": ROOT / "docs",
            "SECURITY": ROOT / ".github",
        }
        for stem, directory in guide_roots.items():
            english_path = directory / f"{stem}.md"
            chinese_path = directory / f"{stem}.zh-CN.md"
            self.assertTrue(english_path.is_file())
            self.assertTrue(chinese_path.is_file())
            self.assertIn(f"[中文说明]({stem}.zh-CN.md)", english_path.read_text(encoding="utf-8"))
            self.assertIn(f"[English]({stem}.md)", chinese_path.read_text(encoding="utf-8"))

    def test_five_illustration_slots_are_stable(self) -> None:
        for filename in ("README.md", "README.zh-CN.md"):
            content = (ROOT / filename).read_text(encoding="utf-8")
            for index in range(0, 5):
                slot = f"ILLUSTRATION_SLOT_{index:02d}"
                self.assertEqual(1, content.count(f"{slot}_START"))
                self.assertEqual(1, content.count(f"{slot}_END"))

        illustrations = (ROOT / "docs" / "ILLUSTRATIONS.md").read_text(encoding="utf-8")
        expected_assets = (
            "00-manuscript-review-studio-overview.png",
            "01-closure-gate.png",
            "02-four-verdicts.png",
            "03-two-axis-separation.png",
            "04-closure-card.png",
        )
        for asset in expected_assets:
            self.assertIn(asset, illustrations)

        expected_dimensions = {
            "00-manuscript-review-studio-overview.png": (1672, 941),
            "01-closure-gate.png": (1672, 941),
            "02-four-verdicts.png": (1672, 941),
            "03-two-axis-separation.png": (1672, 941),
            "04-closure-card.png": (1448, 1086),
        }
        for asset, dimensions in expected_dimensions.items():
            data = (ROOT / "docs" / "images" / asset).read_bytes()
            self.assertEqual(b"\x89PNG\r\n\x1a\n", data[:8])
            self.assertEqual(dimensions, struct.unpack(">II", data[16:24]))
            self.assertIn(f"docs/images/{asset}", (ROOT / "README.md").read_text(encoding="utf-8"))
            self.assertIn(f"docs/images/{asset}", (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"))

    def test_release_governance_files_exist(self) -> None:
        for path in (
            ROOT / "LICENSE",
            ROOT / "NOTICE",
            ROOT / ".github" / "CONTRIBUTING.md",
            ROOT / ".github" / "SECURITY.md",
            ROOT / ".github" / "workflows" / "tests.yml",
            ROOT / "docs" / "CHANGELOG.md",
            ROOT / "docs" / "STANDALONE.zh-CN.md",
            ROOT / "docs" / "THIRD_PARTY_NOTICES.md",
            ROOT / "docs" / "images" / ".gitkeep",
        ):
            self.assertTrue(path.is_file(), str(path))

    def test_all_relative_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        for path in ROOT.rglob("*.md"):
            if any(part in {".git", ".venv", ".build", "release", "__pycache__"} for part in path.parts):
                continue
            content = path.read_text(encoding="utf-8", errors="strict")
            for raw_target in link_pattern.findall(content):
                target = raw_target.strip().strip("<>")
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                relative = target.split("#", 1)[0]
                if not relative:
                    continue
                resolved = (path.parent / relative).resolve()
                self.assertTrue(resolved.exists(), f"broken link in {path}: {raw_target}")

    def test_private_prompt_pack_is_not_published(self) -> None:
        self.assertFalse((ROOT / "ILLUSTRATION_GENERATION_PROMPTS.md").exists())
        self.assertIn("/配图/", (ROOT / ".gitignore").read_text(encoding="utf-8"))
        for path in ROOT.rglob("*"):
            if path.is_file():
                self.assertNotIn("02_local_only", path.as_posix())

    def test_no_absolute_local_paths_or_embedded_credentials(self) -> None:
        forbidden_patterns = {
            "Windows user-profile path": re.compile(
                r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]"
                r"(?:Users|Documents and Settings)[\\/][^\\/\s\"']+"
            ),
            "absolute local drive path": re.compile(
                r"(?i)(?<![A-Za-z0-9])[A-Z]:[\\/]"
                r"(?:[^\\/\r\n]+[\\/]){2,}[^\\/\r\n]+"
            ),
            "credential assignment": re.compile(
                r"(?i)\b(?:api[_-]?key|password|access[_-]?token|secret)\b"
                r"\s*[:=]\s*[\"'][^\"'\r\n]{8,}[\"']"
            ),
            "common hosted-service token": re.compile(
                r"\b(?:github_pat_[A-Za-z0-9_]{20,}|"
                r"gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{20,})\b"
            ),
        }
        for path in ROOT.rglob("*"):
            if (
                not path.is_file()
                or ".git" in path.parts
                or ".venv" in path.parts
                or ".build" in path.parts
                or "release" in path.parts
                or "__pycache__" in path.parts
                or "配图" in path.parts
                or path.name.endswith("_GOAL.zh-CN.md")
                or path.resolve() == Path(__file__).resolve()
                or "test0829" in path.parts
                or path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".jfif", ".pdf", ".docx"}
            ):
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in forbidden_patterns.items():
                self.assertIsNone(pattern.search(content), f"{label} in {path}")


if __name__ == "__main__":
    unittest.main()
