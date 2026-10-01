"""Exercise the actual Windows EXE's public CLI with synthetic loopback providers.

Run after building, optionally setting MRC_FROZEN_EXE and MRC_BUILD_RECEIPT.
The executable runs in fresh temporary directories without source imports.  Only
this acceptance harness imports the sibling mock helpers; no application module
is imported.  Successful synthetic responses prove transport/contract behavior,
not live-provider quality, sample relevance, or journal acceptance likelihood.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from run_frozen_acceptance_0_6_3 import (
    BUILD_RECEIPT,
    EXE,
    MockProvider,
    adjudication_state,
    cause_row,
    coverage_state,
    insufficient_coverage_state,
    provider_env,
    synthetic_manuscript,
    validate_common_runtime,
)


PROVIDER_PAIRS = (
    ("deepseek", "deepseek-v4-pro", "disabled", "high"),
    ("kimi", "kimi-k2.6", "disabled", "enabled"),
    ("gemini", "gemini-2.5-flash", "none", "high"),
)
MODES = (
    ("standard", "moderate", "STANDARD CLOSURE REVIEW"),
    ("strictness", "strict", "STRICT / TOP-TIER REFEREE MODE"),
    ("strictness", "moderate", "MODERATE / BALANCED JOURNAL REFEREE MODE"),
    ("strictness", "lenient", "LENIENT / HIGH REGRESSION-PROTECTION MODE"),
    ("journal_benchmark", "moderate", "TARGET JOURNAL BENCHMARK MODE"),
)
LIMITATIONS = (
    "Synthetic loopback responses only; no real-provider semantic or quality QA.",
    "CLI has no sample-relevance gate; off-topic samples and relevance override are not acceptance-tested as gates.",
    "CLI currently falls back to standard prompts on missing or insufficient samples; a fail-closed sample gate is not implemented.",
    "No rubric extraction stage or rubric-specific budget exists; only the implemented coverage context budget is tested.",
)


class AcceptanceFailure(RuntimeError):
    """A public, bounded failure code without captured output, paths, or secrets."""


def require(condition: object, code: str) -> None:
    if not condition:
        raise AcceptanceFailure(code)


class MultiModeProvider(MockProvider):
    """Supply deterministic, independently authored finite-state fixtures."""

    def _states(self) -> tuple[dict[str, Any], dict[str, Any]]:
        material = self.scenario in {"bounded", "reopen", "bad_digest"}
        dimension = "methods_and_research_design"
        coverage = (
            insufficient_coverage_state() if self.scenario == "insufficient_basis"
            else coverage_state([dimension] if material else [])
        )
        if material:
            for row in coverage["dimensions"]:
                if row["dimension"] == dimension:
                    row["affirmative_sufficiency"] = False
                    row["sufficiency_reason_code"] = "UNRESOLVED_MATERIAL_CONCERN"
        if self.scenario == "invalid_status":
            coverage["dimensions"][0]["status"] = "AFFIRMATIVE_SUFFICIENCY"
        rows = (
            [cause_row(dimension, material=True,
                       scope="central" if self.scenario == "reopen" else "local")]
            if material else []
        )
        adjudication = adjudication_state(coverage, rows)
        if self.scenario == "bad_digest":
            adjudication["coverage_digest_sha256"] = "0" * 64
        return coverage, adjudication


def validate_prompt(request: dict[str, Any], marker: str, *, journal: bool) -> None:
    stage = MockProvider._stage(request)
    system = request["messages"][0]["content"]
    require(marker in system, "MODE_PROMPT_MISSING")
    require("AFFIRMATIVE_SUFFICIENCY" not in system, "LEGACY_INVALID_STATUS_IN_PROMPT")
    require("The current stage schema defines this response." in system, "STAGE_SCHEMA_GUIDANCE_MISSING")
    if stage == "coverage":
        start = "--- COVERAGE ROW EXAMPLES JSON START ---\n"
        end = "\n--- COVERAGE ROW EXAMPLES JSON END ---"
        require(start in system and end in system, "COVERAGE_EXAMPLES_MISSING")
        examples = json.loads(system.split(start, 1)[1].split(end, 1)[0])
        require({row["status"] for row in examples} == {
            "CLEAR", "NON_MATERIAL_CONCERN", "POTENTIAL_MATERIAL_ROOT_CAUSE", "UNASSESSED"
        }, "COVERAGE_EXAMPLES_INVALID")
    elif stage == "adjudication":
        require("--- CURRENT STAGE FIELD RULES: ADJUDICATION ---" in system,
                "ADJUDICATION_GUIDANCE_MISSING")
        require("--- COVERAGE ROW EXAMPLES JSON START ---" not in system,
                "COVERAGE_EXAMPLES_LEAK_TO_ADJUDICATION")
    else:
        raise AcceptanceFailure("UNEXPECTED_PROVIDER_STAGE")
    if journal:
        require("Synthetic Acceptance Journal" in system, "JOURNAL_NAME_MISSING")
        for index in range(5):
            require(f"sample_{index}.md" in system, "JOURNAL_SAMPLE_MISSING")


def validate_reasoning(request: dict[str, Any], provider: str, option: str) -> None:
    if provider in {"deepseek", "kimi"}:
        expected = "disabled" if option == "disabled" else "enabled"
        require(request.get("thinking") == {"type": expected}, "THINKING_CONTROL_MISMATCH")
        if expected == "disabled" or provider == "kimi":
            require("reasoning_effort" not in request, "UNEXPECTED_REASONING_EFFORT")
        else:
            require(request.get("reasoning_effort") == option, "REASONING_EFFORT_MISMATCH")
    else:
        require(request.get("reasoning_effort") == option, "REASONING_EFFORT_MISMATCH")
        require("thinking" not in request, "UNEXPECTED_THINKING_CONTROL")
    expected_format = "json_object" if provider == "deepseek" else "json_schema"
    require(request["response_format"]["type"] == expected_format, "SCHEMA_DELIVERY_MISMATCH")


def comparable_requests(requests: list[dict[str, Any]]) -> str:
    """Remove only requested reasoning controls and random boundary UUIDs."""
    normalized = deepcopy(requests)
    for request in normalized:
        request.pop("thinking", None)
        request.pop("reasoning_effort", None)
        for message in request["messages"]:
            message["content"] = re.sub(r"(?<=_)[0-9a-f]{32}\b", "BOUNDARY_UUID", message["content"])
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def run_case(
    *, provider: str, model: str, reasoning: str,
    mode: str, strictness: str, marker: str,
    scenario: str = "stop", budget_hold: bool = False,
) -> tuple[dict[str, Any], str]:
    with MultiModeProvider(scenario) as mock, tempfile.TemporaryDirectory(prefix="mrc-frozen-modes-") as directory:
        temp = Path(directory)
        # The wrapper may itself run from an empty directory; the child always has
        # its own fresh workspace containing synthetic inputs only.
        require(not list(temp.iterdir()), "WORKSPACE_NOT_EMPTY")
        manuscript = temp / "synthetic.md"
        output = temp / "result.json"
        event_log = temp / "events.jsonl"
        text = synthetic_manuscript()
        if budget_hold:
            text = "# Synthetic context-budget manuscript\n" + "学" * 220_000
        manuscript.write_text(text, encoding="utf-8")
        command = [
            str(EXE), str(manuscript), "--provider", provider, "--model", model,
            "--reasoning", reasoning, "--language", "zh", "--identity", "synthetic-frozen-multimode",
            "--mode", mode, "--strictness", strictness,
            "--confirm-complete", "--consent-to-provider-transmission",
            "--timeout", "20", "--output", str(output), "--event-log", str(event_log),
        ]
        if mode == "journal_benchmark":
            samples = temp / "samples"
            samples.mkdir()
            for index in range(5):
                (samples / f"sample_{index}.md").write_text(
                    f"# Synthetic sample {index}\n" + synthetic_manuscript(), encoding="utf-8"
                )
            command += ["--target-journal-name", "Synthetic Acceptance Journal",
                        "--target-journal-scope", "Synthetic bounded evidence and research design",
                        "--sample-papers-dir", str(samples)]
        env = provider_env(provider, mock.port)
        # Ambient document limits must not change a deterministic acceptance case.
        env["MRC_MAX_FILE_BYTES"] = str(50 * 1024 * 1024)
        env["MRC_MAX_TEXT_CHARS"] = "300000"
        require("PYTHONPATH" not in env and "PYTHONHOME" not in env, "SOURCE_IMPORT_PATH_INHERITED")
        completed = subprocess.run(
            command, cwd=temp, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="strict", timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Never echo the CLI's stdout/stderr: its public result can contain the
        # temporary input path and cannot be copied into the release receipt.
        require(completed.returncode == 0, "CLI_NONZERO_EXIT")
        require(output.is_file() and event_log.is_file(), "OUTPUT_RECEIPT_MISSING")
        result = json.loads(output.read_text(encoding="utf-8"))
        events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines() if line]
        validate_common_runtime(result, events)
        requests = deepcopy(mock.requests)
        runtime = result["runtime"]
        require(runtime["standalone_version"] == BUILD_RECEIPT.get("standalone_version"),
                "RUNTIME_BUILD_VERSION_MISMATCH")
        expected_calls = 0 if budget_hold else 1 if scenario in {"insufficient_basis", "invalid_status"} else 2
        require(len(requests) == expected_calls, "UNEXPECTED_REQUEST_COUNT")
        expected_stages = ["coverage", "adjudication"][:expected_calls]
        require([MockProvider._stage(request) for request in requests] == expected_stages,
                "UNEXPECTED_STAGE_ORDER")
        require(runtime["reasoning_option"] == reasoning, "RECEIPT_REASONING_MISMATCH")
        require(runtime["physical_request_attempt_count"] == expected_calls, "ATTEMPT_COUNT_MISMATCH")
        require(runtime["usage_receipt_count"] == expected_calls, "USAGE_RECEIPT_COUNT_MISMATCH")
        require(runtime["unknown_potential_charge_attempt_count"] == 0, "UNEXPECTED_UNKNOWN_CHARGE")
        require(runtime["usage"].get("total_tokens", 0) == 150 * expected_calls, "USAGE_TOTAL_MISMATCH")
        for request in requests:
            validate_prompt(request, marker, journal=mode == "journal_benchmark")
            validate_reasoning(request, provider, reasoning)
        verdict = {"stop": "STOP_REVISING", "bounded": "ONE_BOUNDED_ROUND",
                   "reopen": "REOPEN_SUBSTANTIVE_REVISION"}.get(scenario, "UNASSESSED")
        if budget_hold:
            verdict = "UNASSESSED"
        require(result["closure_card"]["Verdict"] == verdict, "VERDICT_MISMATCH")
        hold = verdict == "UNASSESSED"
        require(runtime["terminal_status"] == ("HOLD" if hold else "PASS"), "TERMINAL_STATUS_MISMATCH")
        require(runtime["machine_status"] == (
            "NOT_FORMED" if scenario == "insufficient_basis" else "HOLD" if hold else "SUCCEEDED"
        ), "MACHINE_STATUS_MISMATCH")
        require(runtime["presentation_status"] == ("NOT_STARTED" if hold else "PASS"),
                "PRESENTATION_STATUS_MISMATCH")
        if scenario == "insufficient_basis":
            require(result["minimal_receipt"]["reason_category"] == "INSUFFICIENT_WHOLE_MANUSCRIPT_BASIS",
                    "BASIS_HOLD_REASON_MISMATCH")
        if budget_hold:
            require(result["minimal_receipt"]["failed_stage"] == "coverage_context_budget",
                    "BUDGET_HOLD_STAGE_MISMATCH")
            require(runtime["api_called"] is False, "BUDGET_HOLD_DISPATCHED_REQUEST")
            require(any(budget["passed"] is False for budget in runtime["harness"]["context_budgets"]),
                    "FAILED_BUDGET_RECEIPT_MISSING")
        record = {
            "status": "PASS", "provider": provider, "model": model, "reasoning": reasoning,
            "mode": mode, "strictness": strictness, "fixture": "coverage_context_budget" if budget_hold else scenario,
            "requests": expected_calls, "stages": expected_stages, "verdict": verdict,
            "machine_status": runtime["machine_status"], "terminal_status": runtime["terminal_status"],
        }
        return record, comparable_requests(requests)


def main() -> int:
    summary: dict[str, Any] = {
        "suite": "frozen_multimode_mock_acceptance_v1", "status": "FAIL",
        "frozen_exe_sha256": None, "cases": {}, "limitations": list(LIMITATIONS),
        "real_api_calls": 0, "real_manuscripts_read": 0,
        "secret_values_persisted": 0, "raw_responses_persisted": 0,
    }
    try:
        require(os.name == "nt", "WINDOWS_REQUIRED_FOR_FROZEN_ACCEPTANCE")
        require(EXE.is_file(), "FROZEN_EXE_MISSING")
        with EXE.open("rb") as handle:
            require(handle.read(2) == b"MZ", "FROZEN_EXE_NOT_WINDOWS_BINARY")
        digest = hashlib.sha256(EXE.read_bytes()).hexdigest()
        summary["frozen_exe_sha256"] = digest
        require(str(BUILD_RECEIPT.get("sha256", "")).lower() == digest, "BUILD_RECEIPT_SHA256_MISMATCH")
        require(BUILD_RECEIPT.get("bytes") == EXE.stat().st_size, "BUILD_RECEIPT_SIZE_MISMATCH")
        summary["standalone_version"] = BUILD_RECEIPT.get("standalone_version")
        pairs: dict[str, list[str]] = {}
        cases = []
        for provider, model, off, on in PROVIDER_PAIRS:
            for mode, strictness, marker in MODES:
                for reasoning in (off, on):
                    cases.append(dict(provider=provider, model=model, reasoning=reasoning,
                                      mode=mode, strictness=strictness, marker=marker))
            for scenario in ("bounded", "reopen", "insufficient_basis", "invalid_status", "bad_digest"):
                for reasoning in (off, on):
                    cases.append(dict(provider=provider, model=model, reasoning=reasoning,
                                      mode="strictness", strictness="strict", marker=MODES[1][2],
                                      scenario=scenario))
        cases.append(dict(provider="kimi", model="kimi-k2.6", reasoning="disabled",
                          mode="journal_benchmark", strictness="moderate", marker=MODES[4][2],
                          budget_hold=True))
        for case in cases:
            fixture = "coverage_context_budget" if case.get("budget_hold") else case.get("scenario", "stop")
            pair_key = ":".join((case["provider"], case["mode"], case["strictness"], fixture))
            name = pair_key + ":" + case["reasoning"]
            try:
                record, comparable = run_case(**case)
                summary["cases"][name] = record
                if not case.get("budget_hold"):
                    pairs.setdefault(pair_key, []).append(comparable)
                    if len(pairs[pair_key]) == 2:
                        require(pairs[pair_key][0] == pairs[pair_key][1], "OFF_ON_CONTRACT_CHANGED")
                        record["off_on_contract_identical"] = True
            except Exception as exc:
                summary["cases"][name] = {
                    "status": "FAIL", "error_type": type(exc).__name__,
                    "error_code": str(exc) if isinstance(exc, AcceptanceFailure) else "CASE_ASSERTION_OR_EXECUTION_FAILURE",
                }
        summary["case_count"] = len(summary["cases"])
        summary["passed_case_count"] = sum(case["status"] == "PASS" for case in summary["cases"].values())
        summary["failed_case_count"] = summary["case_count"] - summary["passed_case_count"]
        summary["off_on_pair_count"] = sum(len(pair) == 2 and pair[0] == pair[1] for pair in pairs.values())
        if summary["failed_case_count"] == 0:
            summary["status"] = "PASS_FROZEN_MULTIMODE_MOCK_ACCEPTANCE"
    except Exception as exc:
        summary["error_type"] = type(exc).__name__
        summary["error_code"] = str(exc) if isinstance(exc, AcceptanceFailure) else "SETUP_FAILURE"
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["status"] == "PASS_FROZEN_MULTIMODE_MOCK_ACCEPTANCE" else 1


if __name__ == "__main__":
    sys.exit(main())
