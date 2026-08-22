"""Independent RC2.1 probes for receipt schema and Lite clause boundaries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.closure_state import (  # noqa: E402
    SKILL_VERSION,
    ClosureStateError,
    decide_state,
    minimal_receipt,
    public_card,
)


def base_state() -> dict:
    return {
        "manuscript_complete": True,
        "current_identity_clear": True,
        "whole_manuscript_read": True,
        "critical_basis_available": True,
        "bounded_scope": False,
        "current_manuscript_identity": "synthetic-adversarial-rc2-1",
        "material_root_causes": [],
        "evidence_holds": [],
        "submission_holds": [],
        "external_holds": [],
        "evidence_hold_codes": [],
        "submission_hold_codes": [],
        "protected": ["claim ceilings"],
        "parked_opportunities": [],
        "lite_suggestions": [],
        "invalidation_events": [],
        "artifact_only_drift_verified": False,
        "formal_tone": False,
        "rewrite_requested": False,
    }


def local_state() -> dict:
    state = base_state()
    state["material_root_causes"] = [{
        "observed": True,
        "locatable": True,
        "affects": ["argument bridge"],
        "style_only": False,
        "hold_only": False,
        "verification_only": False,
        "expected_benefit_exceeds_risk": True,
        "scope": "local",
    }]
    return state


def expect_reject(thunk) -> None:
    try:
        thunk()
    except ClosureStateError:
        return
    raise AssertionError("probe was accepted")


def main() -> int:
    passed = 0

    def check(name: str, thunk) -> None:
        nonlocal passed
        thunk()
        passed += 1
        print(f"PASS {name}")

    compact = base_state()
    compact["prior_receipt"] = {
        "manuscript_identity": "synthetic-adversarial-rc2-1",
        "verdict": "STOP_REVISING",
    }
    check("schema-absent-compact", lambda: decide_state(compact)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError()))

    legacy = base_state()
    legacy["prior_receipt"] = {
        "manuscript_identity": "synthetic-adversarial-rc2-1",
        "verdict": "STOP_REVISING",
        "evidence_hold_summary": ["source verification required"],
    }
    check("schema-absent-legacy", lambda: decide_state(legacy)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError()))

    for version in ("0.1.0", "0.1.4"):
        state = base_state()
        state["prior_receipt"] = {
            "manuscript_identity": "synthetic-adversarial-rc2-1",
            "verdict": "STOP_REVISING",
            "skill_version": version,
            "evidence_hold_summary": ["source verification required"],
        }
        check(f"schema-legacy-{version}", lambda state=state: decide_state(state)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError()))

    for version in ("0.2.0", "0.2.1"):
        receipt = minimal_receipt(decide_state(base_state()), "synthetic-adversarial-rc2-1", skill_version=version)
        state = base_state()
        state["prior_receipt"] = receipt
        check(f"schema-canonical-{version}", lambda state=state: decide_state(state)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError()))

    for version in (" 0.2.0 ", "0.2.0-rc1", "0.2.0+build1", "0.2.1"):
        state = base_state()
        state["prior_receipt"] = {
            "manuscript_identity": "synthetic-adversarial-rc2-1",
            "verdict": "STOP_REVISING",
            "skill_version": version,
            "evidence_hold_summary": ["source verification required"],
        }
        check(f"schema-legacy-block-{version}", lambda state=state: expect_reject(lambda: decide_state(state)))

    for version in ("0.2.2", "0.3.0", "1.0.0"):
        state = base_state()
        state["prior_receipt"] = {
            "manuscript_identity": "synthetic-adversarial-rc2-1",
            "verdict": "STOP_REVISING",
            "skill_version": version,
            "evidence_hold_codes": [],
            "submission_hold_codes": [],
        }
        check(f"schema-unsupported-{version}", lambda state=state: expect_reject(lambda: decide_state(state)))

    check("schema-default-version", lambda: (
        minimal_receipt(decide_state(base_state()), "synthetic-adversarial-rc2-1")["skill_version"] == SKILL_VERSION == "0.2.1"
    ) or (_ for _ in ()).throw(AssertionError("default version mismatch")))

    separators = (";", "；", ".", "。", "!", "！", "?", "？", ":", "：", ",", "，", "、", "—", "–", "\n", "\r", "\r\n")
    for separator in separators:
        for direction in (
            "Status unresolved" + separator + "rewrite before submission",
            "rewrite before submission" + separator + "Status unresolved",
        ):
            state = local_state()
            state["lite_suggestions"] = [{
                "Direction": direction,
                "Why it matters": "A bounded rationale.",
                "What to protect": "Protect the claim ceiling.",
            }]
            check(f"lite-separator-{repr(separator)}-{len(direction)}", lambda state=state: expect_reject(lambda: public_card(state)))

    for direction in (
        '"rewrite before submission"',
        "(rewrite before submission)",
        "[rewrite before submission]",
        "• rewrite before submission",
        "1) rewrite before submission",
        "（一）重写方法",
    ):
        state = local_state()
        state["lite_suggestions"] = [{
            "Direction": direction,
            "Why it matters": "A bounded rationale.",
            "What to protect": "Protect the claim ceiling.",
        }]
        check(f"lite-wrapper-{len(direction)}", lambda state=state: expect_reject(lambda: public_card(state)))

    for direction in (
        "Clarify the contribution, while preserving the claim ceiling.",
        "Keep the method-to-claim bridge visible.",
        "Preserve source-status distinctions—without overstating completion.",
    ):
        state = local_state()
        state["lite_suggestions"] = [{
            "Direction": direction,
            "Why it matters": "A bounded rationale.",
            "What to protect": "Protect the claim ceiling.",
        }]
        check(f"lite-lawful-{len(direction)}", lambda state=state: public_card(state))

    print(f"ADVERSARIAL_PROBES_RC2_1_OK count={passed}")
    print(json.dumps({"version": SKILL_VERSION, "scope": "schema-and-lite-boundary"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
