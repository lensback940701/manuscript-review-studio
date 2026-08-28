"""Direct frozen-EXE acceptance for the bounded MRC 0.6.3 repair.

Uses only loopback mock providers and synthetic temporary manuscripts.  The
script intentionally imports no application modules, so every assertion is
against the frozen executable's public CLI/GUI behavior and receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "release" / "ManuscriptRevisionClosure.exe"
BUILD_RECEIPT = json.loads((ROOT / "release" / "BUILD_RECEIPT.json").read_text(encoding="utf-8"))

COVERAGE_CONTRACT_VERSION = "mrc-whole-manuscript-coverage-1.0"
COVERAGE_DIMENSIONS = (
    "contribution",
    "whole_paper_argument",
    "theory_and_concepts",
    "methods_and_research_design",
    "evidence_and_analysis",
    "rivals_negative_findings_and_limitations",
    "section_roles_and_coherence",
    "claim_ceiling_and_scope_conditions",
    "evidence_status_and_provenance",
    "revision_vs_submission_boundary",
)


def _canonical_digest(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def coverage_state(candidates: list[str]) -> dict[str, Any]:
    candidate_set = set(candidates)
    return {
        "coverage_contract_version": COVERAGE_CONTRACT_VERSION,
        "manuscript_identity_confirmed": True,
        "full_span_covered": True,
        "dimensions": [
            {
                "dimension": dimension,
                "applicability": "APPLICABLE",
                "assessed": True,
                "status": (
                    "POTENTIAL_MATERIAL_ROOT_CAUSE" if dimension in candidate_set else "CLEAR"
                ),
            }
            for dimension in COVERAGE_DIMENSIONS
        ],
        "root_cause_candidate_dimensions": list(candidates),
        "evidence_hold_codes": [],
        "submission_hold_codes": [],
        "protected_invariants": {
            "claim_ceiling_preserved": True,
            "evidence_status_distinctions_preserved": True,
            "rivals_and_negative_findings_preserved": True,
        },
    }


def cause_row(dimension: str) -> dict[str, Any]:
    return {
        "observed": False,
        "locatable": False,
        "dimension": dimension,
        "style_only": True,
        "hold_only": False,
        "verification_only": False,
        "expected_benefit_exceeds_risk": False,
        "scope": "local",
    }


def adjudication_state(
    coverage: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    protected: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "coverage_digest_sha256": _canonical_digest(coverage),
        "material_root_causes": deepcopy(rows),
        "evidence_hold_codes": [],
        "submission_hold_codes": [],
        "protected": protected or ["保持论点上限和可见的替代解释。"],
        "parked_opportunities": [],
        "lite_suggestions": [],
    }


INTERPRETATION_STATE = {
    "status_explanation": "核心裁决已经完成，不应由一般性实质修改重新打开。",
    "judgment_basis": ["本次判断使用完整当前稿件。", "确定性 Closure Card 提供核心状态。"],
    "judgment_principles": ["材料性根因门槛优先。", "保护论点与证据边界。", "修改截止与投稿准备分轴判断。"],
    "assessment_dimensions": [
        {"dimension": "稿件身份", "finding": "当前身份明确。", "implication": "可以形成整稿判断。"},
        {"dimension": "贡献层级", "finding": "主要贡献可辨认。", "implication": "无需中心重写。"},
        {"dimension": "证据边界", "finding": "现有边界应保护。", "implication": "不得增强主张。"},
        {"dimension": "章节结构", "finding": "章节角色互补。", "implication": "不建议结构重做。"},
        {"dimension": "双轴状态", "finding": "投稿事项独立判断。", "implication": "不能据此重开改稿。"},
    ],
    "selective_findings": [],
    "what_is_stable": ["保持当前贡献层级与证据边界。"],
    "remaining_attention": [],
    "pre_submission_checklist": ["人工核对匿名化要求。", "人工核对作者信息与声明。", "人工核对图表和版权状态。"],
    "optional_micro_adjustments": [],
    "report_limitations": ["没有执行外部事实核验。", "不能替代作者与同行评审判断。"],
    "boundary_note": "本解读不是事实认证、同行评审替代品或投稿授权。",
}


def synthetic_manuscript() -> str:
    return (
        "Synthetic Frozen Acceptance Manuscript\n\nAbstract\n"
        + ("Bounded synthetic argument, evidence, and scope condition.\n" * 90)
        + "\nConclusion\nThe synthetic contribution remains bounded.\n\n"
        + "References\nSynthetic Reference A."
    )


class MockProvider:
    def __init__(self, scenario: str) -> None:
        self.scenario = scenario
        self.requests: list[dict[str, Any]] = []
        self.stages: list[str] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("content-length", "0"))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                stage = outer._stage(body)
                outer.requests.append(body)
                outer.stages.append(stage)
                status, state = outer._response(stage)
                if status != 200:
                    payload = b'{"error":{"message":"bounded mock failure"}}'
                    self.send_response(status)
                    self.send_header("Retry-After", "7")
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                payload = json.dumps(
                    {
                        "model": body.get("model", "mock-model"),
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": json.dumps(state, ensure_ascii=False),
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                    }
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = int(self.server.server_address[1])
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @staticmethod
    def _stage(body: dict[str, Any]) -> str:
        messages = body.get("messages", [])
        system = messages[0].get("content", "") if messages and isinstance(messages[0], dict) else ""
        if "INTERPRETATION AGENT CONTRACT" in system:
            return "interpretation"
        if "whole-manuscript coverage stage" in system:
            return "coverage"
        if "root-cause adjudication stage" in system:
            return "adjudication"
        if "presentation-only localization stage" in system:
            return "presentation_repair"
        raise AssertionError("frozen EXE sent an unrecognized provider stage")

    def _states(self) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.scenario in {"gemini_multi", "gemini_missing", "gemini_duplicate"}:
            coverage = coverage_state(["contribution", "methods_and_research_design"])
        elif self.scenario == "gemini_extra":
            coverage = coverage_state(["contribution"])
        else:
            coverage = coverage_state([])

        if self.scenario == "gemini_missing":
            rows = [cause_row("contribution")]
        elif self.scenario == "gemini_extra":
            rows = [cause_row("contribution"), cause_row("theory_and_concepts")]
        elif self.scenario == "gemini_duplicate":
            rows = [
                cause_row("contribution"),
                cause_row("contribution"),
                cause_row("methods_and_research_design"),
            ]
        else:
            rows = [cause_row(item) for item in coverage["root_cause_candidate_dimensions"]]

        protected = (
            ["Preserve the bounded contribution and visible rival explanations."]
            if self.scenario == "presentation_hold_gui"
            else None
        )
        return coverage, adjudication_state(coverage, rows, protected=protected)

    def _response(self, stage: str) -> tuple[int, dict[str, Any]]:
        coverage, adjudication = self._states()
        if self.scenario in {"gemini_503", "machine_hold_gui"} and stage == "coverage":
            return 503, {}
        if self.scenario == "presentation_hold_gui" and stage == "presentation_repair":
            return 503, {}
        if stage == "coverage":
            if self.scenario == "deepseek_key_mismatch":
                broken = dict(coverage)
                broken["unexpected"] = True
                return 200, broken
            return 200, coverage
        if stage == "adjudication":
            return 200, adjudication
        if stage == "interpretation":
            return 200, INTERPRETATION_STATE
        raise AssertionError(f"unexpected stage {stage}")

    def __enter__(self) -> "MockProvider":
        self.thread.start()
        return self

    def __exit__(self, _kind: object, _value: object, _traceback: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise AssertionError("mock provider server did not stop")


def provider_env(provider: str, port: int) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "MOONSHOT_API_KEY",
        "KIMI_API_KEY",
        "KIMI_BASE_URL",
        "GEMINI_API_KEY",
        "GEMINI_BASE_URL",
    ):
        env.pop(key, None)
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "ALL_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
        }
    )
    base = f"http://127.0.0.1:{port}"
    if provider == "deepseek":
        env.update({"DEEPSEEK_API_KEY": "mock", "DEEPSEEK_BASE_URL": base})
    elif provider == "kimi":
        env.update({"MOONSHOT_API_KEY": "mock", "KIMI_BASE_URL": base})
    elif provider == "gemini":
        env.update({"GEMINI_API_KEY": "mock", "GEMINI_BASE_URL": base})
    else:
        raise AssertionError("unknown provider")
    return env


def validate_common_runtime(result: dict[str, Any], events: list[dict[str, Any]]) -> None:
    runtime = result["runtime"]
    attempts = [event for event in events if event.get("type") == "provider.attempt"]
    terminal = [event for event in events if event.get("type") in {"turn.completed", "turn.failed"}]
    assert len(terminal) == 1, terminal
    for event in attempts:
        assert event.get("provider")
        assert event.get("model")
        assert event.get("reasoning_option")
        assert event.get("max_transient_retries") == 0
        assert event.get("retry_decision") == "STOP_NO_AUTOMATIC_RETRY"
    assert runtime["provider_call_count"] == runtime["physical_request_attempt_count"]
    assert runtime["raw_provider_response_persisted"] is False
    serialized = json.dumps(result, ensure_ascii=False)
    assert "Authorization" not in serialized
    assert '"api_key"' not in serialized
    assert "bounded mock failure" not in serialized


def run_cli_case(
    scenario: str,
    provider: str,
    model: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    with MockProvider(scenario) as mock, tempfile.TemporaryDirectory(prefix="mrc063-frozen-cli-") as directory:
        temp = Path(directory)
        manuscript = temp / "synthetic.md"
        output = temp / "result.json"
        event_log = temp / "events.jsonl"
        manuscript.write_text(synthetic_manuscript(), encoding="utf-8")
        completed = subprocess.run(
            [
                str(EXE),
                str(manuscript),
                "--provider",
                provider,
                "--model",
                model,
                "--reasoning",
                "default",
                "--language",
                "zh",
                "--identity",
                f"synthetic-{scenario}",
                "--confirm-complete",
                "--output",
                str(output),
                "--event-log",
                str(event_log),
            ],
            cwd=temp,
            env=provider_env(provider, mock.port),
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert completed.returncode == 0, (scenario, completed.stdout, completed.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines() if line]
        validate_common_runtime(result, events)
        requests = deepcopy(mock.requests)
    return result, events, requests


def _request_json(url: str, token: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="GET" if payload is None else "POST",
        headers={"X-MRC-Token": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def run_gui_case(
    scenario: str,
    provider: str,
    model: str,
    *,
    interpretation: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with MockProvider(scenario) as mock, tempfile.TemporaryDirectory(prefix="mrc063-frozen-gui-") as directory:
        temp = Path(directory)
        manuscript = temp / "synthetic.md"
        manuscript.write_text(synthetic_manuscript(), encoding="utf-8")
        process = subprocess.Popen(
            [str(EXE), "--gui-no-browser"],
            cwd=temp,
            env=provider_env(provider, mock.port),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        try:
            assert process.stdout is not None
            line = process.stdout.readline().strip()
            assert line.startswith("Local GUI URL: "), line
            gui_url = line.split(": ", 1)[1]
            parsed = urllib.parse.urlsplit(gui_url)
            token = urllib.parse.parse_qs(parsed.query)["token"][0]
            base = f"{parsed.scheme}://{parsed.netloc}"
            accepted = _request_json(
                base + "/api/analyze",
                token,
                payload={
                    "manuscript_path": str(manuscript),
                    "provider": provider,
                    "model": model,
                    "reasoning_option": "default",
                    "language": "zh",
                    "identity": f"synthetic-{scenario}",
                    "confirmed_complete": True,
                    "prior_receipt_path": "",
                    "generate_interpretation": interpretation,
                },
            )
            assert accepted["accepted"] is True
            deadline = time.monotonic() + 60
            snapshot: dict[str, Any] = {}
            while time.monotonic() < deadline:
                snapshot = _request_json(base + "/api/status", token)
                if not snapshot.get("busy"):
                    break
                time.sleep(0.05)
            assert snapshot and not snapshot.get("busy"), snapshot
            _request_json(base + "/api/close", token, payload={})
            process.wait(timeout=10)
            assert process.returncode == 0
            requests = deepcopy(mock.requests)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        assert not list(temp.iterdir()) or list(temp.iterdir()) == [manuscript]
    return snapshot, requests


def main() -> None:
    assert EXE.is_file()
    assert BUILD_RECEIPT["standalone_version"] == "0.6.3"
    summary: dict[str, Any] = {"frozen_exe_sha256": hashlib.sha256(EXE.read_bytes()).hexdigest(), "cases": {}}

    kimi, kimi_requests = run_gui_case(
        "kimi_positive_gui", "kimi", "kimi-k2.6", interpretation=True
    )
    assert kimi["phase"] == "completed"
    kimi_runtime = kimi["result"]["runtime"]
    assert kimi_runtime["machine_status"] == "SUCCEEDED"
    assert kimi_runtime["presentation_status"] == "PASS"
    assert kimi_runtime["terminal_status"] == "PASS"
    assert [MockProvider._stage(request) for request in kimi_requests] == [
        "coverage",
        "adjudication",
        "interpretation",
    ]
    assert kimi["result"]["task_cost"]["physical_request_attempt_count"] == 3
    assert kimi["result"]["task_cost"]["usage_receipt_count"] == 3
    assert kimi["result"]["task_cost"]["unknown_potential_charge_attempt_count"] == 0
    assert sum("terminal_event_id" in item.get("details", {}) for item in kimi["timeline"]) == 1
    summary["cases"]["kimi_positive_gui"] = {"requests": 3, "phase": kimi["phase"]}

    transient, _events, transient_requests = run_cli_case(
        "gemini_503", "gemini", "gemini-3.7-flash"
    )
    transient_runtime = transient["runtime"]
    assert len(transient_requests) == 1
    assert transient_runtime["machine_status"] == "HOLD"
    assert transient_runtime["presentation_status"] == "NOT_STARTED"
    assert transient_runtime["physical_request_attempt_count"] == 1
    assert transient_runtime["unknown_potential_charge_attempt_count"] == 1
    physical = transient_runtime["physical_request_receipts"][0]
    assert physical["http_status"] == 503
    assert physical["provider_outcome"] == "UNKNOWN"
    assert physical["retry_after"] == "7"
    assert "稿件完整性：PASS" in transient["closure_card"]["Reason"]
    summary["cases"]["gemini_503"] = {"requests": 1, "machine_status": "HOLD"}

    multi, _events, multi_requests = run_cli_case(
        "gemini_multi", "gemini", "gemini-3.6-flash"
    )
    assert multi["runtime"]["machine_status"] == "SUCCEEDED"
    assert multi["runtime"]["presentation_status"] == "PASS"
    dynamic = multi_requests[1]["response_format"]["json_schema"]["schema"]
    cause_schema = dynamic["properties"]["material_root_causes"]
    assert cause_schema["minItems"] == cause_schema["maxItems"] == 2
    assert cause_schema["items"]["properties"]["dimension"]["enum"] == [
        "contribution",
        "methods_and_research_design",
    ]
    summary["cases"]["gemini_multi"] = {"requests": 2, "dynamic_candidates": 2}

    for scenario, field, expected in (
        ("gemini_missing", "missing_candidates", ["methods_and_research_design"]),
        ("gemini_extra", "extra_candidates", ["theory_and_concepts"]),
        ("gemini_duplicate", "duplicate_candidates", ["contribution"]),
    ):
        result, _events, requests = run_cli_case(scenario, "gemini", "gemini-3.6-flash")
        runtime = result["runtime"]
        assert len(requests) == 2
        assert runtime["machine_status"] == "HOLD"
        assert runtime["presentation_status"] == "NOT_STARTED"
        assert runtime["machine_receipt"]["authoritative_presentation_source"] is None
        assert runtime["machine_receipt"]["authoritative_candidate_state"] is False
        diagnostic = runtime["machine_receipt"]["bounded_contract_failure"]
        for required_field in (
            "required_candidates",
            "observed_candidates",
            "missing_candidates",
            "extra_candidates",
            "duplicate_candidates",
        ):
            assert required_field in diagnostic
        assert diagnostic[field] == expected
        summary["cases"][scenario] = {"requests": 2, field: expected}

    deepseek, _events, deepseek_requests = run_cli_case(
        "deepseek_valid", "deepseek", "deepseek-v4-pro"
    )
    assert deepseek["runtime"]["machine_status"] == "SUCCEEDED"
    assert len(deepseek_requests) == 2
    for request in deepseek_requests:
        assert request["response_format"] == {"type": "json_object"}
        system = request["messages"][0]["content"]
        assert "Canonical JSON schema:" in system
        assert "Canonical schema SHA-256:" in system
    assert BUILD_RECEIPT["coverage_schema_sha256"] in deepseek_requests[0]["messages"][0]["content"]
    summary["cases"]["deepseek_valid"] = {"requests": 2, "schema_in_prompt": True}

    mismatch, _events, mismatch_requests = run_cli_case(
        "deepseek_key_mismatch", "deepseek", "deepseek-v4-pro"
    )
    assert len(mismatch_requests) == 1
    mismatch_runtime = mismatch["runtime"]
    assert mismatch_runtime["machine_status"] == "HOLD"
    diagnostic = mismatch_runtime["machine_receipt"]["bounded_contract_failure"]
    assert diagnostic["failed_path"] == "$"
    assert diagnostic["extra_keys"] == ["unexpected"]
    assert diagnostic["schema_sha256"] == BUILD_RECEIPT["coverage_schema_sha256"]
    summary["cases"]["deepseek_key_mismatch"] = {"requests": 1, "extra_keys": ["unexpected"]}

    machine_gui, machine_gui_requests = run_gui_case(
        "machine_hold_gui", "gemini", "gemini-3.7-flash", interpretation=False
    )
    assert len(machine_gui_requests) == 1
    assert machine_gui["phase"] == "completed_with_machine_hold"
    assert machine_gui["result"]["runtime"]["presentation_status"] == "NOT_STARTED"
    assert "机器裁决未形成" in machine_gui["message"]
    summary["cases"]["machine_hold_gui"] = {"requests": 1, "phase": machine_gui["phase"]}

    presentation_gui, presentation_gui_requests = run_gui_case(
        "presentation_hold_gui", "gemini", "gemini-3.6-flash", interpretation=False
    )
    assert len(presentation_gui_requests) == 3
    assert presentation_gui["phase"] == "completed_with_presentation_hold"
    assert presentation_gui["result"]["runtime"]["machine_status"] == "SUCCEEDED"
    assert presentation_gui["result"]["runtime"]["presentation_status"] == "HOLD"
    assert "机器裁决已完成" in presentation_gui["message"]
    summary["cases"]["presentation_hold_gui"] = {
        "requests": 3,
        "phase": presentation_gui["phase"],
    }

    summary.update(
        {
            "status": "PASS_FROZEN_MRC_0_6_3_MOCK_ACCEPTANCE",
            "case_count": len(summary["cases"]),
            "real_api_calls": 0,
            "real_manuscripts_read": 0,
            "secret_values_persisted": 0,
            "raw_responses_persisted": 0,
        }
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
