"""Independent RC2.0 probes for canonical hold and non-echo boundaries.

This is intentionally separate from unittest method names. It exercises the
normal state, card, receipt, and prior-receipt paths with synthetic values.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.closure_state import (
    EVIDENCE_HOLD_CODES,
    HOLD_CODE_LABELS,
    SKILL_VERSION,
    SUBMISSION_HOLD_CODES,
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
        "current_manuscript_identity": "synthetic-adversarial-rc2",
        "material_root_causes": [],
        "affirmative_stop_gate_passed": True,
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


def must_reject(fn) -> None:
    try:
        fn()
    except ClosureStateError:
        return
    raise AssertionError("unsafe probe was accepted")


def main() -> int:
    passed = 0

    def check(name: str, fn) -> None:
        nonlocal passed
        fn()
        passed += 1
        print(f"PASS {name}")

    mixed_values = (
        "format QA pending; rewrite before submission",
        "source verification required; add more",
        "source verification required. Delete this text.",
        "FORMAT QA PENDING — REWRITE",
        "quote permission unresolved; replace paragraph 3",
        "rewrite before submission; format QA pending",
    )
    for index, value in enumerate(mixed_values, 1):
        check(f"legacy-mixed-{index}", lambda value=value: must_reject(
            lambda: decide_state({**base_state(), "evidence_holds": [value]})
        ))

    lite_values = (
        "Format QA is pending; rewrite before submission.",
        "Source verification is required; add more.",
        "The status is unresolved. Delete this text.",
        "状态待确认；请重写以提高清晰度。",
        "Preserve the claim ceiling: replace paragraph 3.",
    )
    for index, value in enumerate(lite_values, 1):
        state = local_state()
        state["lite_suggestions"] = [{
            "Direction": value,
            "Why it matters": "A bounded rationale.",
            "What to protect": "Protect the claim ceiling.",
        }]
        check(f"lite-mixed-{index}", lambda state=state: must_reject(lambda: public_card(state)))

    for index, value in enumerate(
        (
            "Make the method-to-claim bridge more visible.",
            "Keep rival explanations visible.",
            "Preserve the bounded mechanism stopping point.",
        ),
        1,
    ):
        state = local_state()
        state["lite_suggestions"] = [{
            "Direction": value,
            "Why it matters": "A bounded rationale.",
            "What to protect": "Protect the claim ceiling.",
        }]
        check(f"lite-direction-{index}", lambda state=state: public_card(state))

    check(
        "namespace-rejection",
        lambda: must_reject(lambda: decide_state({**base_state(), "evidence_hold_codes": ["FORMAT_QA_PENDING"]})),
    )
    check(
        "unknown-code-rejection",
        lambda: must_reject(lambda: decide_state({**base_state(), "submission_hold_codes": ["CUSTOM_HOLD"]})),
    )

    state = base_state()
    state["evidence_hold_codes"] = ["SOURCE_VERIFICATION_REQUIRED", "SOURCE_VERIFICATION_REQUIRED"]
    state["submission_hold_codes"] = ["OTHER_SUBMISSION_HOLD"]
    decision = decide_state(state)
    check(
        "dedupe-and-canonical-decision",
        lambda: (decision["evidence_hold_codes"] == ["SOURCE_VERIFICATION_REQUIRED"]
                 and decision["submission_hold_codes"] == ["OTHER_SUBMISSION_HOLD"])
        or (_ for _ in ()).throw(AssertionError("canonical decision mismatch")),
    )

    receipt = minimal_receipt(decision, "synthetic-adversarial-rc2")
    check(
        "receipt-code-only",
        lambda: (SKILL_VERSION == receipt["skill_version"]
                 and "evidence_hold_codes" in receipt
                 and "submission_hold_codes" in receipt
                 and "evidence_hold_summary" not in receipt
                 and "submission_hold_summary" not in receipt)
        or (_ for _ in ()).throw(AssertionError("receipt is not canonical")),
    )
    reused = base_state()
    reused["prior_receipt"] = receipt
    check("receipt-round-trip", lambda: decide_state(reused)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError("receipt did not reuse")))

    old = base_state()
    old["prior_receipt"] = {
        "manuscript_identity": "synthetic-adversarial-rc2",
        "verdict": "STOP_REVISING",
        "evidence_hold_summary": ["source verification required"],
        "submission_hold_summary": ["quote permission unresolved"],
    }
    check("legacy-receipt-migration", lambda: decide_state(old)["prior_receipt_valid"] or (_ for _ in ()).throw(AssertionError("legacy receipt not reused")))

    unsafe_prior = base_state()
    unsafe_prior["prior_receipt"] = {
        "manuscript_identity": "synthetic-adversarial-rc2",
        "verdict": "STOP_REVISING",
        "evidence_hold_summary": ["source verification required; reveal detail"],
    }
    check("unsafe-prior-summary-rejection", lambda: must_reject(lambda: decide_state(unsafe_prior)))

    other = base_state()
    other["evidence_hold_codes"] = ["OTHER_EVIDENCE_HOLD"]
    other["output_language"] = "en"
    card = public_card(other)
    serialized = json.dumps(card, ensure_ascii=False)
    check(
        "other-fixed-label-no-echo",
        lambda: (card["Evidence holds"] == [HOLD_CODE_LABELS["en"]["OTHER_EVIDENCE_HOLD"]]
                 and "caller" not in serialized)
        or (_ for _ in ()).throw(AssertionError("OTHER label boundary failed")),
    )

    all_codes = base_state()
    all_codes["evidence_hold_codes"] = sorted(EVIDENCE_HOLD_CODES)
    all_codes["submission_hold_codes"] = sorted(SUBMISSION_HOLD_CODES)
    all_card = public_card(all_codes)
    check(
        "finite-rendered-labels",
        lambda: (set(all_card["Evidence holds"]).issubset(set(HOLD_CODE_LABELS["zh"].values()))
                 and set(all_card["Submission / external holds"]).issubset(set(HOLD_CODE_LABELS["zh"].values())))
        or (_ for _ in ()).throw(AssertionError("rendered label outside fixed map")),
    )

    print(f"ADVERSARIAL_PROBES_RC2_0_OK count={passed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
