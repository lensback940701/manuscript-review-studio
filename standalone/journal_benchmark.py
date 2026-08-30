"""Sample paper ingestion, target journal profiling, and relevance preflight."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .document_reader import read_document


SUPPORTED_SAMPLE_EXTENSIONS = {".pdf", ".md", ".txt", ".docx", ".html", ".htm"}
MINIMUM_SAMPLE_PAPERS = 5


@dataclass(slots=True, frozen=True)
class SamplePaperSummary:
    filename: str
    artifact_sha256: str
    character_count: int
    estimated_heading_count: int
    text_preview: str


@dataclass(slots=True, frozen=True)
class JournalBenchmarkProfile:
    target_journal_name: str
    target_journal_scope: str
    sample_papers_count: int
    samples: tuple[SamplePaperSummary, ...]

    def build_samples_summary_text(self, max_samples: int = 8, max_chars_per_sample: int = 500) -> str:
        """Format sample papers into a rich context block for prompts."""
        items = []
        for idx, s in enumerate(self.samples[:max_samples], start=1):
            clean_prev = " ".join(s.text_preview[:max_chars_per_sample].split())
            items.append(f"  [样本 {idx}] 文件: {s.filename} (约 {s.character_count:,} 字) | 摘录: {clean_prev}...")
        return "\n".join(items)


@dataclass(slots=True, frozen=True)
class SampleRelevanceResult:
    rating: str  # "HIGH", "MODERATE", "LOW"
    score: float  # 0.0 to 1.0
    explanation: str
    methodological_alignment: str
    theoretical_alignment: str
    recommendation: str
    is_suitable: bool


def find_sample_paper_files(directory: Path | str) -> list[Path]:
    """Scan directory for supported sample paper files."""
    path = Path(directory).resolve()
    if not path.is_dir():
        raise ValueError(f"样本目录不存在或不是文件夹 / Sample directory does not exist: {path}")

    files: list[Path] = []
    for item in path.iterdir():
        if item.is_file() and item.suffix.lower() in SUPPORTED_SAMPLE_EXTENSIONS:
            files.append(item)
    return sorted(files, key=lambda f: f.name.lower())


def ingest_sample_papers(
    sample_directory: Path | str,
    *,
    target_journal_name: str = "",
    target_journal_scope: str = "",
) -> JournalBenchmarkProfile:
    """Ingest and summarize all sample papers in the given directory."""
    files = find_sample_paper_files(sample_directory)
    if len(files) < MINIMUM_SAMPLE_PAPERS:
        raise ValueError(
            f"目标期刊样本论文数量不足：至少需要 {MINIMUM_SAMPLE_PAPERS} 篇已发表相关论文，当前仅找到 {len(files)} 篇。"
            f" / Minimum {MINIMUM_SAMPLE_PAPERS} sample papers required, found {len(files)}."
        )

    samples: list[SamplePaperSummary] = []
    for file_path in files:
        try:
            doc = read_document(file_path)
            preview = doc.text[:3000].strip()
            headings_est = doc.text.count("\n# ") + doc.text.count("\n## ") + doc.text.count("\n### ")
            samples.append(
                SamplePaperSummary(
                    filename=file_path.name,
                    artifact_sha256=doc.artifact_sha256,
                    character_count=len(doc.text),
                    estimated_heading_count=headings_est,
                    text_preview=preview,
                )
            )
        except Exception as exc:
            raise ValueError(f"读取样本论文失败 ({file_path.name}): {exc}") from exc

    return JournalBenchmarkProfile(
        target_journal_name=target_journal_name.strip(),
        target_journal_scope=target_journal_scope.strip(),
        sample_papers_count=len(samples),
        samples=tuple(samples),
    )


def evaluate_sample_relevance_prompt(
    manuscript_text: str,
    benchmark_profile: JournalBenchmarkProfile,
) -> list[dict[str, str]]:
    """Build messages for evaluating the relevance between the manuscript and sample papers."""
    manuscript_summary = manuscript_text[:4000]

    samples_block = []
    for i, s in enumerate(benchmark_profile.samples[:10], start=1):
        samples_block.append(
            f"--- 样本论文 {i}: {s.filename} (字数: {s.character_count}) ---\n{s.text_preview}\n"
        )
    samples_text = "\n".join(samples_block)

    system = """你是一个权威学术期刊同行评审与方法学专家。
你的任务是评估待测稿件（Manuscript）与用户提供的【目标期刊样本论文库（Sample Papers）】之间的相关性与范式匹配度。

请严格返回如下格式的 JSON 对象，不得返回任何 Markdown 标记或多余文字：
{
  "rating": "HIGH" | "MODERATE" | "LOW",
  "score": 0.0 到 1.0 之间的浮点数,
  "explanation": "简明分析样本与稿件在研究主题、学科领域与问题导向上的匹配情况（50-150字中文）",
  "methodological_alignment": "方法学范式匹配分析（如质性案例 vs 计量实证 vs 混合方法的一致性，50-100字中文）",
  "theoretical_alignment": "理论对话与概念体系的契合度分析（50-100字中文）",
  "recommendation": "明确的行动建议（如：样本高度匹配可直接对准 / 建议补充更多同类型方法样本 / 样本偏差较大建议更换，30-80字中文）",
  "is_suitable": true | false
}
"""
    user = f"""目标期刊名称：{benchmark_profile.target_journal_name or "未指定"}
目标期刊 Scope/定位：{benchmark_profile.target_journal_scope or "未提供"}
样本论文总数：{benchmark_profile.sample_papers_count} 篇

=== 待测论文摘录（前 4000 字符） ===
{manuscript_summary}

=== 样本论文库摘录 ===
{samples_text}

请评估待测稿件与样本论文库的匹配度，返回唯一的 JSON 对象："""

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_sample_relevance_response(response_text: str) -> SampleRelevanceResult:
    """Parse and validate the JSON response from sample relevance evaluation."""
    clean = response_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"样本相关性评估未返回有效 JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("样本相关性评估返回值必须为单一 JSON 对象")

    rating = str(data.get("rating", "MODERATE")).upper()
    if rating not in {"HIGH", "MODERATE", "LOW"}:
        rating = "MODERATE"

    try:
        score = float(data.get("score", 0.5))
        score = max(0.0, min(1.0, score))
    except (ValueError, TypeError):
        score = 0.5

    return SampleRelevanceResult(
        rating=rating,
        score=score,
        explanation=str(data.get("explanation", "")).strip(),
        methodological_alignment=str(data.get("methodological_alignment", "")).strip(),
        theoretical_alignment=str(data.get("theoretical_alignment", "")).strip(),
        recommendation=str(data.get("recommendation", "")).strip(),
        is_suitable=bool(data.get("is_suitable", rating in {"HIGH", "MODERATE"})),
    )
