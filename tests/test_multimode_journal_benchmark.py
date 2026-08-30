"""Tests for multi-mode evaluation, strictness profiles, and target journal benchmark features."""

import json
import tempfile
import unittest
from pathlib import Path

from standalone.assessor import RunOptions
from standalone.harness import (
    EVALUATION_MODES,
    STRICTNESS_LEVELS,
    validate_mode,
    validate_strictness,
)
from standalone.journal_benchmark import (
    MINIMUM_SAMPLE_PAPERS,
    JournalBenchmarkProfile,
    SamplePaperSummary,
    SampleRelevanceResult,
    evaluate_sample_relevance_prompt,
    find_sample_paper_files,
    ingest_sample_papers,
    parse_sample_relevance_response,
)
from standalone.prompting import (
    build_adjudication_messages,
    build_coverage_messages,
)


class MultiModeHarnessTests(unittest.TestCase):
    def test_mode_and_strictness_validation(self):
        self.assertEqual(validate_mode("standard"), "standard")
        self.assertEqual(validate_mode("strictness"), "strictness")
        self.assertEqual(validate_mode("journal_benchmark"), "journal_benchmark")
        self.assertEqual(validate_mode(None), "standard")

        with self.assertRaises(ValueError):
            validate_mode("invalid_mode")

        self.assertEqual(validate_strictness("strict"), "strict")
        self.assertEqual(validate_strictness("moderate"), "moderate")
        self.assertEqual(validate_strictness("lenient"), "lenient")
        self.assertEqual(validate_strictness(None), "moderate")

        with self.assertRaises(ValueError):
            validate_strictness("super_hard")


class JournalBenchmarkIngestionTests(unittest.TestCase):
    def test_ingest_sample_papers_success_and_minimum_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Insufficient papers (less than 5)
            dummy_1k = "# Sample Paper\n" + "This is substantive academic paper text. " * 50
            for i in range(3):
                (tmppath / f"paper_{i}.md").write_text(f"# Paper {i}\n{dummy_1k}", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                ingest_sample_papers(tmppath)
            self.assertIn("至少需要 5 篇", str(ctx.exception))

            # Add more to reach 5
            for i in range(3, 6):
                (tmppath / f"paper_{i}.txt").write_text(f"Abstract {i}\n{dummy_1k}", encoding="utf-8")

            profile = ingest_sample_papers(
                tmppath,
                target_journal_name="Research Policy",
                target_journal_scope="Innovation and transitions",
            )
            self.assertEqual(profile.target_journal_name, "Research Policy")
            self.assertEqual(profile.target_journal_scope, "Innovation and transitions")
            self.assertEqual(profile.sample_papers_count, 6)
            self.assertEqual(len(profile.samples), 6)
            self.assertTrue(all(isinstance(s, SamplePaperSummary) for s in profile.samples))


class SampleRelevanceEvaluationTests(unittest.TestCase):
    def test_evaluate_sample_relevance_prompt_generation(self):
        profile = JournalBenchmarkProfile(
            target_journal_name="World Development",
            target_journal_scope="Development economics and rural transformation",
            sample_papers_count=5,
            samples=(
                SamplePaperSummary("s1.pdf", "sha1", 10000, 5, "Sample 1 abstract"),
                SamplePaperSummary("s2.pdf", "sha2", 12000, 6, "Sample 2 abstract"),
                SamplePaperSummary("s3.pdf", "sha3", 11000, 4, "Sample 3 abstract"),
                SamplePaperSummary("s4.pdf", "sha4", 13000, 7, "Sample 4 abstract"),
                SamplePaperSummary("s5.pdf", "sha5", 14000, 8, "Sample 5 abstract"),
            ),
        )
        manuscript = "# Coffee Transformation in Yunnan\nAbstract: This paper explores..."
        messages = evaluate_sample_relevance_prompt(manuscript, profile)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("样本论文库", messages[0]["content"])
        self.assertIn("World Development", messages[1]["content"])
        self.assertIn("s1.pdf", messages[1]["content"])

    def test_parse_sample_relevance_response_valid_and_fallback(self):
        valid_json = """```json
        {
          "rating": "HIGH",
          "score": 0.92,
          "explanation": "高度契合发展经济学与农业转型主题",
          "methodological_alignment": "均为定性过程追踪",
          "theoretical_alignment": "同属社会技术转型理论体系",
          "recommendation": "可直接作为目标基准",
          "is_suitable": true
        }
        ```"""
        res = parse_sample_relevance_response(valid_json)
        self.assertEqual(res.rating, "HIGH")
        self.assertAlmostEqual(res.score, 0.92)
        self.assertTrue(res.is_suitable)
        self.assertIn("高度契合", res.explanation)

        # Low rating test
        low_json = """{
          "rating": "LOW",
          "score": 0.25,
          "explanation": "样本全为微观计量经济学，稿件为纯质性案例",
          "methodological_alignment": "范式差异显著",
          "theoretical_alignment": "理论侧重不同",
          "recommendation": "建议更换定性案例样本",
          "is_suitable": false
        }"""
        res_low = parse_sample_relevance_response(low_json)
        self.assertEqual(res_low.rating, "LOW")
        self.assertFalse(res_low.is_suitable)


class MultiModePromptingTests(unittest.TestCase):
    def test_coverage_prompt_with_strictness_and_journal_mode(self):
        manuscript = "# Test Title\n## S1 Intro\nContent..."

        # Mode 1: Standard
        std_msgs = build_coverage_messages(manuscript, manuscript_identity="doc1", mode="standard")
        self.assertIn("STANDARD CLOSURE REVIEW", std_msgs[0]["content"])

        # Mode 2: Strict
        strict_msgs = build_coverage_messages(
            manuscript, manuscript_identity="doc1", mode="strictness", strictness_level="strict"
        )
        self.assertIn("STRICT / TOP-TIER REFEREE MODE", strict_msgs[0]["content"])
        self.assertIn("严厉尺度", strict_msgs[0]["content"])

        # Mode 2: Lenient
        lenient_msgs = build_coverage_messages(
            manuscript, manuscript_identity="doc1", mode="strictness", strictness_level="lenient"
        )
        self.assertIn("LENIENT / HIGH REGRESSION-PROTECTION MODE", lenient_msgs[0]["content"])
        self.assertIn("宽松尺度", lenient_msgs[0]["content"])

        # Mode 3: Journal Benchmark
        profile = JournalBenchmarkProfile(
            target_journal_name="Research Policy",
            target_journal_scope="Innovation Policy",
            sample_papers_count=5,
            samples=(
                SamplePaperSummary("p1.md", "sha1", 5000, 3, "P1 preview"),
                SamplePaperSummary("p2.md", "sha2", 5000, 3, "P2 preview"),
                SamplePaperSummary("p3.md", "sha3", 5000, 3, "P3 preview"),
                SamplePaperSummary("p4.md", "sha4", 5000, 3, "P4 preview"),
                SamplePaperSummary("p5.md", "sha5", 5000, 3, "P5 preview"),
            ),
        )
        journal_msgs = build_coverage_messages(
            manuscript,
            manuscript_identity="doc1",
            mode="journal_benchmark",
            benchmark_profile=profile,
        )
        self.assertIn("TARGET JOURNAL BENCHMARK MODE", journal_msgs[0]["content"])
        self.assertIn("Research Policy", journal_msgs[0]["content"])
        self.assertIn("p1.md", journal_msgs[0]["content"])


class RunOptionsMultiModeTests(unittest.TestCase):
    def test_run_options_defaults_and_customization(self):
        opts = RunOptions(manuscript_path=Path("dummy.md"))
        self.assertEqual(opts.mode, "standard")
        self.assertEqual(opts.strictness_level, "moderate")
        self.assertEqual(opts.target_journal_name, "")
        self.assertIsNone(opts.sample_papers_dir)

        custom = RunOptions(
            manuscript_path=Path("dummy.md"),
            mode="journal_benchmark",
            strictness_level="strict",
            target_journal_name="World Development",
            target_journal_scope="Rural economics",
            sample_papers_dir=Path("/path/to/samples"),
            sample_relevance_override=True,
        )
        self.assertEqual(custom.mode, "journal_benchmark")
        self.assertEqual(custom.strictness_level, "strict")
        self.assertEqual(custom.target_journal_name, "World Development")
        self.assertTrue(custom.sample_relevance_override)


if __name__ == "__main__":
    unittest.main()
