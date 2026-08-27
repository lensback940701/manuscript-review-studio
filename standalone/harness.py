"""Deterministic intake, context, and cross-stage harness contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.closure_state import EVIDENCE_HOLD_CODES, SUBMISSION_HOLD_CODES


INTAKE_CONTRACT_VERSION = "mrc-manuscript-intake-1.0"
COVERAGE_CONTRACT_VERSION = "mrc-whole-manuscript-coverage-1.0"
ADJUDICATION_CONTRACT_VERSION = "mrc-root-cause-adjudication-1.0"
CONTRADICTION_GATE_VERSION = "mrc-cross-stage-contradiction-gate-1.0"

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
COVERAGE_STATUSES = frozenset(
    {"CLEAR", "NON_MATERIAL_CONCERN", "POTENTIAL_MATERIAL_ROOT_CAUSE", "UNASSESSED"}
)
APPLICABILITY_STATES = frozenset({"APPLICABLE", "NOT_APPLICABLE"})
PROTECTED_INVARIANT_KEYS = frozenset(
    {
        "claim_ceiling_preserved",
        "evidence_status_distinctions_preserved",
        "rivals_and_negative_findings_preserved",
    }
)
DIMENSION_KEYS = frozenset({"dimension", "applicability", "assessed", "status"})


class HarnessContractError(ValueError):
    """Raised when a deterministic or model harness contract fails closed."""


@dataclass(frozen=True, slots=True)
class IntakeReceipt:
    character_count: int
    title_present: bool
    abstract_present: bool
    conclusion_present: bool
    references_present: bool
    conclusion_before_references: bool
    heading_count: int
    complete_structure: bool
    contract_version: str = INTAKE_CONTRACT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "character_count": self.character_count,
            "title_present": self.title_present,
            "abstract_present": self.abstract_present,
            "conclusion_present": self.conclusion_present,
            "references_present": self.references_present,
            "conclusion_before_references": self.conclusion_before_references,
            "heading_count": self.heading_count,
            "complete_structure": self.complete_structure,
        }


@dataclass(frozen=True, slots=True)
class ContextBudgetReceipt:
    provider: str
    model: str
    context_limit_tokens: int
    estimated_input_tokens: int
    safety_margin_tokens: int
    requested_max_output_tokens: int
    passed: bool
    estimator: str = "mrc-conservative-mixed-script-token-estimator-1.0"

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "context_limit_tokens": self.context_limit_tokens,
            "estimated_input_tokens": self.estimated_input_tokens,
            "safety_margin_tokens": self.safety_margin_tokens,
            "requested_max_output_tokens": self.requested_max_output_tokens,
            "passed": self.passed,
            "estimator": self.estimator,
        }


_ABSTRACT_RE = re.compile(r"^(?:\d+(?:\.\d+)*[\s.)、-]*)?(?:abstract|摘要)\s*[:：]?$", re.I)
_CONCLUSION_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*[\s.)、-]*)?(?:conclusions?|discussion\s+and\s+conclusions?|"
    r"concluding\s+discussion|结论|结语|讨论与结论|结论与讨论)\s*[:：]?$",
    re.I,
)
_REFERENCES_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*[\s.)、-]*)?(?:references|bibliography|works\s+cited|参考文献|参考资料)\s*[:：]?$",
    re.I,
)
_HEADING_RE = re.compile(r"^(?:#{1,6}\s+|\d+(?:\.\d+)*[\s.)、]+|[一二三四五六七八九十]+、)")


def _clean_heading(line: str) -> str:
    value = line.strip().strip("#").strip()
    return " ".join(value.split())


def analyze_intake_structure(text: str, *, minimum_characters: int = 1000) -> IntakeReceipt:
    lines = [_clean_heading(line) for line in text.splitlines()]
    content_lines = [
        (index, line)
        for index, line in enumerate(lines)
        if line and not (line.startswith("---") and line.endswith("---"))
    ]
    title_present = bool(content_lines and 2 <= len(content_lines[0][1]) <= 300)
    abstract_positions = [index for index, line in content_lines if _ABSTRACT_RE.fullmatch(line)]
    conclusion_positions = [index for index, line in content_lines if _CONCLUSION_RE.fullmatch(line)]
    reference_positions = [index for index, line in content_lines if _REFERENCES_RE.fullmatch(line)]
    abstract_present = bool(abstract_positions)
    conclusion_present = bool(conclusion_positions)
    references_present = bool(reference_positions)
    conclusion_before_references = bool(
        conclusion_positions and reference_positions and min(conclusion_positions) < max(reference_positions)
    )
    heading_count = sum(
        1
        for _index, line in content_lines
        if len(line) <= 140
        and (
            _HEADING_RE.match(line)
            or _ABSTRACT_RE.fullmatch(line)
            or _CONCLUSION_RE.fullmatch(line)
            or _REFERENCES_RE.fullmatch(line)
        )
    )
    complete = all(
        (
            len(text.strip()) >= minimum_characters,
            title_present,
            abstract_present,
            conclusion_present,
            references_present,
            conclusion_before_references,
            heading_count >= 3,
        )
    )
    return IntakeReceipt(
        character_count=len(text),
        title_present=title_present,
        abstract_present=abstract_present,
        conclusion_present=conclusion_present,
        references_present=references_present,
        conclusion_before_references=conclusion_before_references,
        heading_count=heading_count,
        complete_structure=complete,
    )


def provider_context_limit(provider: str, model: str) -> int:
    name = provider.casefold().strip()
    model_id = model.casefold().strip()
    if name == "deepseek":
        return 1_048_576
    if name == "kimi":
        if model_id == "kimi-k3":
            return 1_048_576
        if model_id.startswith(("kimi-k2.5", "kimi-k2.6", "kimi-k2.7")):
            return 262_144
        return 131_072
    if name == "gemini":
        return 1_048_576
    raise HarnessContractError("context budget requires one registered provider")


def provider_output_ceiling(provider: str) -> int:
    return {"deepseek": 393_216, "kimi": 131_072, "gemini": 65_536}[provider]


def estimate_message_tokens(messages: Sequence[Mapping[str, str]]) -> int:
    text = "\n".join(str(message.get("content", "")) for message in messages)
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text))
    ascii_visible = len(re.findall(r"[\x21-\x7e]", text))
    other = max(0, len(text) - cjk - ascii_visible)
    estimate = cjk + ascii_visible / 3.0 + other / 2.0
    return int(math.ceil(estimate * 1.30)) + 2048


def context_budget(
    messages: Sequence[Mapping[str, str]],
    *,
    provider: str,
    model: str,
    minimum_output_tokens: int = 8192,
) -> ContextBudgetReceipt:
    context_limit = provider_context_limit(provider, model)
    estimated_input = estimate_message_tokens(messages)
    safety_margin = max(4096, int(context_limit * 0.03))
    remaining = context_limit - estimated_input - safety_margin
    requested = min(provider_output_ceiling(provider), max(0, remaining))
    return ContextBudgetReceipt(
        provider=provider,
        model=model,
        context_limit_tokens=context_limit,
        estimated_input_tokens=estimated_input,
        safety_margin_tokens=safety_margin,
        requested_max_output_tokens=requested,
        passed=requested >= minimum_output_tokens,
    )


COVERAGE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "coverage_contract_version",
        "manuscript_identity_confirmed",
        "full_span_covered",
        "dimensions",
        "root_cause_candidate_dimensions",
        "evidence_hold_codes",
        "submission_hold_codes",
        "protected_invariants",
    ],
    "properties": {
        "coverage_contract_version": {"type": "string", "enum": [COVERAGE_CONTRACT_VERSION]},
        "manuscript_identity_confirmed": {"type": "boolean"},
        "full_span_covered": {"type": "boolean"},
        "dimensions": {
            "type": "array",
            "minItems": len(COVERAGE_DIMENSIONS),
            "maxItems": len(COVERAGE_DIMENSIONS),
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(DIMENSION_KEYS),
                "properties": {
                    "dimension": {"type": "string", "enum": list(COVERAGE_DIMENSIONS)},
                    "applicability": {"type": "string", "enum": sorted(APPLICABILITY_STATES)},
                    "assessed": {"type": "boolean"},
                    "status": {"type": "string", "enum": sorted(COVERAGE_STATUSES)},
                },
            },
        },
        "root_cause_candidate_dimensions": {
            "type": "array",
            "items": {"type": "string", "enum": list(COVERAGE_DIMENSIONS)},
        },
        "evidence_hold_codes": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(EVIDENCE_HOLD_CODES)},
        },
        "submission_hold_codes": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(SUBMISSION_HOLD_CODES)},
        },
        "protected_invariants": {
            "type": "object",
            "additionalProperties": False,
            "required": sorted(PROTECTED_INVARIANT_KEYS),
            "properties": {key: {"type": "boolean"} for key in sorted(PROTECTED_INVARIANT_KEYS)},
        },
    },
}


def validate_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != set(COVERAGE_JSON_SCHEMA["required"]):
        raise HarnessContractError("coverage output key set mismatch")
    if value["coverage_contract_version"] != COVERAGE_CONTRACT_VERSION:
        raise HarnessContractError("coverage contract version mismatch")
    for field in ("manuscript_identity_confirmed", "full_span_covered"):
        if not isinstance(value[field], bool):
            raise HarnessContractError(f"coverage {field} must be boolean")
    dimensions = value["dimensions"]
    if not isinstance(dimensions, list) or len(dimensions) != len(COVERAGE_DIMENSIONS):
        raise HarnessContractError("coverage dimensions must have the exact required cardinality")
    clean_dimensions: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    for row in dimensions:
        if not isinstance(row, Mapping) or set(row) != DIMENSION_KEYS:
            raise HarnessContractError("coverage dimension row key set mismatch")
        dimension = row["dimension"]
        if dimension not in COVERAGE_DIMENSIONS:
            raise HarnessContractError("coverage contains an unknown dimension")
        if row["applicability"] not in APPLICABILITY_STATES:
            raise HarnessContractError("coverage applicability is invalid")
        if not isinstance(row["assessed"], bool) or row["status"] not in COVERAGE_STATUSES:
            raise HarnessContractError("coverage assessment state is invalid")
        if row["applicability"] == "NOT_APPLICABLE" and row["status"] not in {"CLEAR", "UNASSESSED"}:
            raise HarnessContractError("not-applicable coverage cannot claim a material concern")
        if not row["assessed"] and row["status"] != "UNASSESSED":
            raise HarnessContractError("unassessed dimension must use UNASSESSED status")
        if row["assessed"] and row["status"] == "UNASSESSED":
            raise HarnessContractError("assessed dimension cannot use UNASSESSED status")
        observed_ids.append(dimension)
        clean_dimensions.append(dict(row))
    if set(observed_ids) != set(COVERAGE_DIMENSIONS) or len(set(observed_ids)) != len(observed_ids):
        raise HarnessContractError("coverage dimension set must match exactly without duplicates")
    candidate_dimensions = value["root_cause_candidate_dimensions"]
    if not isinstance(candidate_dimensions, list) or any(item not in COVERAGE_DIMENSIONS for item in candidate_dimensions):
        raise HarnessContractError("coverage root-cause candidate dimensions are invalid")
    if len(set(candidate_dimensions)) != len(candidate_dimensions):
        raise HarnessContractError("coverage root-cause candidate dimensions contain duplicates")
    expected_candidates = {
        row["dimension"] for row in clean_dimensions if row["status"] == "POTENTIAL_MATERIAL_ROOT_CAUSE"
    }
    if set(candidate_dimensions) != expected_candidates:
        raise HarnessContractError("coverage candidate list does not match dimension states")
    evidence = value["evidence_hold_codes"]
    submission = value["submission_hold_codes"]
    if not isinstance(evidence, list) or any(code not in EVIDENCE_HOLD_CODES for code in evidence):
        raise HarnessContractError("coverage evidence hold codes are invalid")
    if not isinstance(submission, list) or any(code not in SUBMISSION_HOLD_CODES for code in submission):
        raise HarnessContractError("coverage submission hold codes are invalid")
    invariants = value["protected_invariants"]
    if not isinstance(invariants, Mapping) or set(invariants) != PROTECTED_INVARIANT_KEYS:
        raise HarnessContractError("coverage protected invariant key set mismatch")
    if any(not isinstance(invariants[key], bool) for key in PROTECTED_INVARIANT_KEYS):
        raise HarnessContractError("coverage protected invariants must be boolean")
    return {
        "coverage_contract_version": COVERAGE_CONTRACT_VERSION,
        "manuscript_identity_confirmed": value["manuscript_identity_confirmed"],
        "full_span_covered": value["full_span_covered"],
        "dimensions": clean_dimensions,
        "root_cause_candidate_dimensions": list(candidate_dimensions),
        "evidence_hold_codes": list(dict.fromkeys(evidence)),
        "submission_hold_codes": list(dict.fromkeys(submission)),
        "protected_invariants": dict(invariants),
    }


def coverage_is_complete(coverage: Mapping[str, Any]) -> bool:
    return bool(
        coverage["manuscript_identity_confirmed"]
        and coverage["full_span_covered"]
        and all(row["assessed"] and row["status"] != "UNASSESSED" for row in coverage["dimensions"])
    )


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


ADJUDICATION_BINDING_KEYS = frozenset({"coverage_digest_sha256"})


def validate_adjudication_binding(value: Mapping[str, Any], coverage: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HarnessContractError("adjudication output must be one object")
    expected_digest = canonical_digest(coverage)
    if value.get("coverage_digest_sha256") != expected_digest:
        raise HarnessContractError("adjudication coverage digest binding mismatch")
    return {key: value[key] for key in value if key not in ADJUDICATION_BINDING_KEYS}


def validate_cross_stage_consistency(coverage: Mapping[str, Any], model_state: Mapping[str, Any]) -> None:
    candidates = list(coverage["root_cause_candidate_dimensions"])
    occurrences: list[str] = []
    for cause in model_state["material_root_causes"]:
        affects = cause["affects"]
        if any(item not in COVERAGE_DIMENSIONS for item in affects):
            raise HarnessContractError("adjudication root cause references an unknown coverage dimension")
        occurrences.extend(affects)
    if set(occurrences) != set(candidates) or len(occurrences) != len(set(occurrences)):
        raise HarnessContractError("adjudication must account for every coverage candidate exactly once")
    if not set(coverage["evidence_hold_codes"]).issubset(model_state["evidence_hold_codes"]):
        raise HarnessContractError("adjudication silently dropped a coverage evidence hold")
    if not set(coverage["submission_hold_codes"]).issubset(model_state["submission_hold_codes"]):
        raise HarnessContractError("adjudication silently dropped a coverage submission hold")
    invariant_dimensions = {
        "claim_ceiling_preserved": "claim_ceiling_and_scope_conditions",
        "evidence_status_distinctions_preserved": "evidence_status_and_provenance",
        "rivals_and_negative_findings_preserved": "rivals_negative_findings_and_limitations",
    }
    for key, dimension in invariant_dimensions.items():
        if not coverage["protected_invariants"][key] and dimension not in candidates:
            raise HarnessContractError("coverage invariant failure lacks a root-cause candidate dimension")


def harness_receipt(
    intake: IntakeReceipt,
    budgets: Sequence[ContextBudgetReceipt],
    *,
    coverage: Mapping[str, Any] | None = None,
    adjudication_bound: bool = False,
    contradiction_gate_passed: bool = False,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "intake": intake.as_dict(),
        "context_budgets": [budget.as_dict() for budget in budgets],
        "coverage_contract_version": COVERAGE_CONTRACT_VERSION,
        "adjudication_contract_version": ADJUDICATION_CONTRACT_VERSION,
        "contradiction_gate_version": CONTRADICTION_GATE_VERSION,
        "coverage_completed": False,
        "coverage_dimension_count": 0,
        "coverage_digest_sha256": None,
        "adjudication_coverage_binding": adjudication_bound,
        "contradiction_gate_passed": contradiction_gate_passed,
    }
    if coverage is not None:
        receipt.update(
            {
                "coverage_completed": coverage_is_complete(coverage),
                "coverage_dimension_count": len(coverage["dimensions"]),
                "coverage_digest_sha256": canonical_digest(coverage),
            }
        )
    return receipt
