"""Offline contracts: model reasoning controls cannot change assessment contracts.

These tests exercise real serialization, parsing, validation and reduction with synthetic
HTTP responses. They do not assert that a live model produces the supplied fixtures.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from standalone.assessor import RunOptions, analyze_manuscript
from standalone.harness import (
    AFFIRMATIVE_STOP_DIMENSIONS,
    COVERAGE_CONTRACT_VERSION,
    COVERAGE_DIMENSIONS,
    COVERAGE_STATUSES,
    HarnessContractError,
    canonical_digest,
    validate_coverage,
)
from standalone.journal_benchmark import JournalBenchmarkProfile, SamplePaperSummary
from standalone.prompting import build_adjudication_messages, build_coverage_messages
from standalone.providers import ProviderConfig, reasoning_profile


# Every named OFF-capable model in the registered reasoning contracts, including K2.5.
PROVIDER_PAIRS = (
    ("deepseek", "deepseek-v4-pro", "disabled", "high"),
    ("deepseek", "deepseek-v4-flash", "disabled", "low"),
    ("deepseek", "deepseek-v4-flash-vision-exp", "disabled", "max"),
    ("kimi", "kimi-k2.5", "disabled", "enabled"),
    ("kimi", "kimi-k2.6", "disabled", "enabled"),
    ("gemini", "gemini-2.5-flash", "none", "high"),
    ("gemini", "gemini-2.5-flash-lite", "none", "low"),
)
MODE_CASES = (
    ("standard", "moderate"),
    ("strictness", "strict"),
    ("strictness", "moderate"),
    ("strictness", "lenient"),
    ("journal_benchmark", "moderate"),
)
PROFILE = JournalBenchmarkProfile(
    "Synthetic Journal", "Synthetic bounded evidence", 5,
    tuple(SamplePaperSummary(f"sample_{i}.txt", f"synthetic_{i}", 100, 0,
                             "Synthetic academic sample.") for i in range(5)),
)


def coverage_fixture(outcome: str = "STOP_REVISING") -> dict:
    sufficient = outcome != "UNASSESSED"
    material = outcome in {"ONE_BOUNDED_ROUND", "REOPEN_SUBSTANTIVE_REVISION"}
    candidate = "methods_and_research_design"
    return {
        "coverage_contract_version": COVERAGE_CONTRACT_VERSION,
        "whole_manuscript_basis": "SUFFICIENT" if sufficient else "INSUFFICIENT",
        "basis_reason_codes": ["SUFFICIENT_SUBSTANTIVE_WHOLE_MANUSCRIPT" if sufficient
                               else "FRAGMENT_OR_EXCERPT_ONLY"],
        "basis_explanation": "Synthetic whole-manuscript basis." if sufficient
                             else "Synthetic material is only a fragment.",
        "manuscript_identity_confirmed": True,
        "full_span_covered": sufficient,
        "dimensions": [
            {"dimension": dimension, "applicability": "APPLICABLE", "assessed": sufficient,
             "status": "UNASSESSED" if not sufficient else
                       "POTENTIAL_MATERIAL_ROOT_CAUSE" if material and dimension == candidate else "CLEAR",
             "affirmative_sufficiency": sufficient and not (material and dimension == candidate),
             "sufficiency_reason_code": "UNASSESSED" if not sufficient else
                 "UNRESOLVED_MATERIAL_CONCERN" if material and dimension == candidate else
                 "AFFIRMATIVE_MANUSCRIPT_SUPPORT"}
            for dimension in COVERAGE_DIMENSIONS
        ],
        "root_cause_candidate_dimensions": [candidate] if material else [],
        "evidence_hold_codes": [],
        "submission_hold_codes": [],
        "protected_invariants": {key: sufficient for key in
            ("claim_ceiling_preserved", "evidence_status_distinctions_preserved",
             "rivals_and_negative_findings_preserved")},
    }


def adjudication_fixture(coverage: dict, outcome: str) -> dict:
    candidate = "methods_and_research_design"
    material = outcome in {"ONE_BOUNDED_ROUND", "REOPEN_SUBSTANTIVE_REVISION"}
    cause = {
        "dimension": candidate, "observed": True, "locatable": True,
        "origin": "COVERAGE_CANDIDATE", "coverage_disagreement": False,
        "disposition_reason_code": "MATERIAL_CONCERN_CONFIRMED",
        "author_decision_required": False, "style_only": False, "hold_only": False,
        "verification_only": False, "expected_benefit_exceeds_risk": True,
        "scope": "central" if outcome == "REOPEN_SUBSTANTIVE_REVISION" else "local",
    }
    return {
        "coverage_digest_sha256": canonical_digest(coverage),
        "material_root_causes": [cause] if material else [],
        "affirmative_sufficiency": [
            {"dimension": dimension, "assessed": True,
             "affirmative_sufficiency": not (material and dimension == candidate),
             "unresolved_material_concern": material and dimension == candidate,
             "sufficiency_reason_code": "UNRESOLVED_MATERIAL_CONCERN"
                 if material and dimension == candidate else "AFFIRMATIVE_MANUSCRIPT_SUPPORT"}
            for dimension in AFFIRMATIVE_STOP_DIMENSIONS
        ],
        "evidence_hold_codes": [], "submission_hold_codes": [],
        "protected": [], "parked_opportunities": [], "lite_suggestions": [],
    }


class ReasoningModeContractTests(unittest.TestCase):
    def _run(self, provider, model, option, mode, strictness, outcome, *, corrupt=None, response_override=None):
        coverage = coverage_fixture(outcome)
        adjudication = adjudication_fixture(coverage, outcome)
        if corrupt is not None:
            corrupt(coverage, adjudication)
        captured = []
        responses = [coverage, adjudication]

        def fake_urlopen(request, timeout):
            self.assertGreater(timeout, 0)
            self.assertEqual(request.full_url, "http://127.0.0.1:8765/chat/completions")
            body = json.loads(request.data)
            captured.append(body)
            self.assertLessEqual(len(captured), 2, "No automatic repair/resend is authorized")
            # OFF responses intentionally have no reasoning_content field. ON may have
            # one, but it is never needed to parse or validate the final answer.
            message = {"content": json.dumps(responses[len(captured) - 1])}
            if option not in {"disabled", "none"}:
                message["reasoning_content"] = "PRIVATE_REASONING_SENTINEL"
            payload = {
                "model": model,
                "choices": [{"message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }
            if response_override is not None:
                response_override(len(captured), payload)
            return io.BytesIO(json.dumps(payload).encode())

        config = ProviderConfig(provider, model, "http://127.0.0.1:8765", "mock", "TEST_KEY")
        with tempfile.TemporaryDirectory() as directory:
            manuscript = Path(directory) / "synthetic.md"
            manuscript.write_text("# Synthetic Manuscript\n" +
                                  "Bounded synthetic argument and evidence.\n" * 80,
                                  encoding="utf-8")
            with patch("standalone.assessor.load_provider_config", return_value=config), \
                 patch("standalone.assessor.ingest_sample_papers", return_value=PROFILE), \
                 patch("standalone.providers.urllib.request.urlopen", side_effect=fake_urlopen), \
                 patch("standalone.prompting.uuid.uuid4", return_value=uuid.UUID(int=1)):
                result = analyze_manuscript(RunOptions(
                    manuscript_path=manuscript, manuscript_identity="synthetic-current",
                    provider=provider, model=model, reasoning_option=option,
                    provider_transmission_consent=True, output_language="en",
                    mode=mode, strictness_level=strictness,
                    sample_papers_dir=Path(directory) if mode == "journal_benchmark" else None,
                ))
        self.assertNotIn("PRIVATE_REASONING_SENTINEL", json.dumps(result.as_dict()))
        return result, captured

    def test_off_on_full_pipeline_matrix_preserves_all_four_verdicts(self):
        # 7 model contracts x 5 calibrations x 4 outcomes x OFF/ON = 280 runs.
        for provider, model, off, on in PROVIDER_PAIRS:
            registered = {item["value"] for item in reasoning_profile(provider, model)["options"]}
            self.assertTrue({off, on}.issubset(registered))
            for mode, strictness in MODE_CASES:
                for outcome in ("STOP_REVISING", "ONE_BOUNDED_ROUND",
                                "REOPEN_SUBSTANTIVE_REVISION", "UNASSESSED"):
                    pair_requests = []
                    for option in (off, on):
                        with self.subTest(provider=provider, model=model, option=option,
                                          mode=mode, strictness=strictness, outcome=outcome):
                            result, requests = self._run(provider, model, option, mode, strictness, outcome)
                            self.assertEqual(outcome, result.closure_card["Verdict"])
                            self.assertEqual(option, result.reasoning_option)
                            calls = 1 if outcome == "UNASSESSED" else 2
                            self.assertEqual(calls, len(requests))
                            self.assertEqual(calls, result.attempts)
                            self.assertEqual(10 * calls, result.usage["prompt_tokens"])
                            self.assertEqual(20 * calls, result.usage["completion_tokens"])
                            for request in requests:
                                if provider in {"deepseek", "kimi"}:
                                    self.assertEqual("disabled" if option == off else "enabled",
                                                     request["thinking"]["type"])
                                    if option == off:
                                        self.assertNotIn("reasoning_effort", request)
                                else:
                                    self.assertEqual(option, request["reasoning_effort"])
                                    self.assertNotIn("thinking", request)
                                self.assertEqual("json_object" if provider == "deepseek" else "json_schema",
                                                 request["response_format"]["type"])
                            self.assertEqual("HOLD" if outcome == "UNASSESSED" else "PASS",
                                             result.run_status["terminal_status"])
                            pair_requests.append([{k: v for k, v in request.items()
                                                   if k not in {"thinking", "reasoning_effort"}}
                                                  for request in requests])
                    self.assertEqual(pair_requests[0], pair_requests[1],
                                     "Thinking controls must not change prompts, schemas, or mode")

    def test_empty_refused_and_truncated_completions_preserve_stage_usage_off_and_on(self):
        for provider, model, off, on in PROVIDER_PAIRS:
            for option in (off, on):
                for failed_call in (1, 2):
                    for reason, code in (("stop", "EMPTY_COMPLETION_CONTENT"),
                                         ("length", "TRUNCATED_COMPLETION"),
                                         ("content_filter", "REFUSED_COMPLETION")):
                        with self.subTest(provider=provider, model=model, option=option,
                                          stage=failed_call, reason=reason):
                            def response_override(call, payload):
                                if call == failed_call:
                                    payload["choices"][0].update(
                                        message={"content": None,
                                                 "reasoning_content": "PRIVATE_REASONING_SENTINEL"},
                                        finish_reason=reason)
                            result, requests = self._run(
                                provider, model, option, "strictness", "strict", "STOP_REVISING",
                                response_override=response_override)
                            self.assertEqual("HOLD", result.run_status["terminal_status"])
                            self.assertEqual("UNASSESSED", result.closure_card["Verdict"])
                            self.assertEqual(failed_call, len(requests))
                            self.assertEqual(failed_call, result.attempts)
                            self.assertEqual("COMPLETE", result.run_status["usage_status"])
                            self.assertEqual(10 * failed_call, result.usage["prompt_tokens"])
                            self.assertEqual(20 * failed_call, result.usage["completion_tokens"])
                            stage = result.provider_receipts[-1]
                            self.assertEqual("coverage" if failed_call == 1 else "adjudication", stage["stage"])
                            self.assertEqual(reason, stage["finish_reason"])
                            self.assertEqual({"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}, stage["usage"])
                            self.assertEqual("COMPLETE", stage["usage_status"])
                            physical = stage["physical_request_receipts"][0]
                            self.assertEqual(code, physical["completion_error_code"])
                            self.assertEqual(reason, physical["finish_reason"])
                            self.assertEqual(option, physical["reasoning_option"])

    def test_prompt_coverage_examples_obey_the_actual_validator_in_all_modes(self):
        for mode, strictness in MODE_CASES:
            with self.subTest(mode=mode, strictness=strictness):
                messages = build_coverage_messages("Synthetic input", manuscript_identity="test",
                    mode=mode, strictness_level=strictness, benchmark_profile=PROFILE)
                prompt = messages[0]["content"]
                self.assertNotIn("AFFIRMATIVE_SUFFICIENCY", prompt)
                encoded = prompt.split("--- COVERAGE ROW EXAMPLES JSON START ---\n", 1)[1].split(
                    "\n--- COVERAGE ROW EXAMPLES JSON END ---", 1)[0]
                examples = json.loads(encoded)
                self.assertEqual(set(COVERAGE_STATUSES), {row["status"] for row in examples})
                for example in examples:
                    fixture = coverage_fixture()
                    fixture["dimensions"][0].update(example)
                    fixture["root_cause_candidate_dimensions"] = (
                        ["contribution"] if example["status"] == "POTENTIAL_MATERIAL_ROOT_CAUSE" else [])
                    validate_coverage(fixture)
                adjudication = build_adjudication_messages("Synthetic input", manuscript_identity="test",
                    output_language="en", coverage=coverage_fixture(), mode=mode,
                    strictness_level=strictness, benchmark_profile=PROFILE)[0]["content"]
                self.assertNotIn("--- COVERAGE ROW EXAMPLES JSON START ---", adjudication)
                self.assertIn("--- CURRENT STAGE FIELD RULES: ADJUDICATION ---", adjudication)
                self.assertIn("The current stage schema defines this response.", adjudication)

    def test_original_lenient_instruction_value_remains_invalid_not_silently_repaired(self):
        # The old lenient prompt told a model to classify as AFFIRMATIVE_SUFFICIENCY,
        # which is not a legal status. Correct the instruction, not the validator.
        fixture = coverage_fixture()
        fixture["dimensions"][0]["status"] = "AFFIRMATIVE_SUFFICIENCY"
        with self.assertRaises(HarnessContractError):
            validate_coverage(fixture)

    def test_bad_mode_two_output_fails_closed_equally_off_and_on_without_resend(self):
        def bad_status(coverage, _adjudication):
            coverage["dimensions"][0]["status"] = "AFFIRMATIVE_SUFFICIENCY"

        def bad_digest(_coverage, adjudication):
            adjudication["coverage_digest_sha256"] = "wrong-digest"

        def missing_candidate(_coverage, adjudication):
            adjudication["material_root_causes"] = []

        def contradictory_sufficiency(_coverage, adjudication):
            adjudication["affirmative_sufficiency"][3].update(
                affirmative_sufficiency=True, unresolved_material_concern=False,
                sufficiency_reason_code="AFFIRMATIVE_MANUSCRIPT_SUPPORT")

        for provider, model, off, on in PROVIDER_PAIRS:
            for option in (off, on):
                for corrupt, calls in ((bad_status, 1), (bad_digest, 2),
                                       (missing_candidate, 2), (contradictory_sufficiency, 2)):
                    with self.subTest(provider=provider, model=model, option=option, corrupt=corrupt.__name__):
                        result, requests = self._run(provider, model, option, "strictness", "strict",
                                                     "ONE_BOUNDED_ROUND", corrupt=corrupt)
                        self.assertEqual("UNASSESSED", result.closure_card["Verdict"])
                        self.assertEqual("HOLD", result.run_status["terminal_status"])
                        self.assertEqual(calls, len(requests))
                        self.assertEqual(calls, result.attempts)
                        self.assertEqual(option, result.reasoning_option)


if __name__ == "__main__":
    unittest.main()
