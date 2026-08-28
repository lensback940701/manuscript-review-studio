"""Deterministic intake, context, and cross-stage harness contracts."""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from scripts.closure_state import EVIDENCE_HOLD_CODES, SUBMISSION_HOLD_CODES


INTAKE_CONTRACT_VERSION = "mrc-manuscript-intake-1.0"
COVERAGE_CONTRACT_VERSION = "mrc-whole-manuscript-coverage-1.0"
ADJUDICATION_CONTRACT_VERSION = "mrc-root-cause-adjudication-1.0"
CONTRADICTION_GATE_VERSION = "mrc-cross-stage-contradiction-gate-1.0"
SCHEMA_DELIVERY_CONTRACT_VERSION = "mrc-canonical-schema-delivery-1.0"
DYNAMIC_ADJUDICATION_SCHEMA_VERSION = "mrc-dynamic-adjudication-schema-1.0"
CANDIDATE_EXACT_SET_CONTRACT_VERSION = "mrc-candidate-exact-set-1.0"

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


class SchemaContractError(HarnessContractError):
    """Raised with a bounded path/key receipt for one canonical JSON schema failure."""

    def __init__(self, message: str, receipt: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.contract_receipt = dict(receipt)


class CandidateSetContractError(HarnessContractError):
    """Raised when adjudication does not account for the frozen candidate set exactly once."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        super().__init__("adjudication must account for every coverage candidate exactly once")
        self.contract_receipt = dict(receipt)


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


ADJUDICATION_REQUIRED_KEYS = [
    "coverage_digest_sha256",
    "material_root_causes",
    "evidence_hold_codes",
    "submission_hold_codes",
    "protected",
    "parked_opportunities",
    "lite_suggestions",
]


_ADJUDICATION_SCHEMA_TEMPLATE: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ADJUDICATION_REQUIRED_KEYS,
    "properties": {
        "coverage_digest_sha256": {"type": "string"},
        "material_root_causes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "observed",
                    "locatable",
                    "dimension",
                    "style_only",
                    "hold_only",
                    "verification_only",
                    "expected_benefit_exceeds_risk",
                    "scope",
                ],
                "properties": {
                    "observed": {"type": "boolean"},
                    "locatable": {"type": "boolean"},
                    "dimension": {"type": "string", "enum": []},
                    "style_only": {"type": "boolean"},
                    "hold_only": {"type": "boolean"},
                    "verification_only": {"type": "boolean"},
                    "expected_benefit_exceeds_risk": {"type": "boolean"},
                    "scope": {"type": "string", "enum": ["local", "central"]},
                },
            },
        },
        "evidence_hold_codes": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(EVIDENCE_HOLD_CODES)},
        },
        "submission_hold_codes": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(SUBMISSION_HOLD_CODES)},
        },
        "protected": {
            "type": "array",
            "maxItems": 5,
            "items": {"type": "string", "maxLength": 240},
        },
        "parked_opportunities": {
            "type": "array",
            "maxItems": 2,
            "items": {"type": "string", "maxLength": 240},
        },
        "lite_suggestions": {
            "type": "array",
            "maxItems": 3,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["Direction", "Why it matters", "What to protect"],
                "properties": {
                    "Direction": {"type": "string", "maxLength": 240},
                    "Why it matters": {"type": "string", "maxLength": 240},
                    "What to protect": {"type": "string", "maxLength": 240},
                },
            },
        },
    },
}


def canonical_json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def schema_sha256(schema: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_text(schema).encode("utf-8")).hexdigest()


def _candidate_ids(coverage: Mapping[str, Any]) -> list[str]:
    observed = coverage.get("root_cause_candidate_dimensions", [])
    if not isinstance(observed, list) or any(item not in COVERAGE_DIMENSIONS for item in observed):
        raise HarnessContractError("coverage root-cause candidate dimensions are invalid")
    if len(set(observed)) != len(observed):
        raise HarnessContractError("coverage root-cause candidate dimensions contain duplicates")
    order = {dimension: index for index, dimension in enumerate(COVERAGE_DIMENSIONS)}
    return sorted(observed, key=order.__getitem__)


def build_adjudication_json_schema(coverage: Mapping[str, Any]) -> dict[str, Any]:
    """Bind the canonical adjudication schema to this run's frozen candidate identities."""

    candidates = _candidate_ids(coverage)
    schema = deepcopy(_ADJUDICATION_SCHEMA_TEMPLATE)
    causes = schema["properties"]["material_root_causes"]
    causes["minItems"] = len(candidates)
    causes["maxItems"] = len(candidates)
    causes["items"]["properties"]["dimension"]["enum"] = candidates
    return schema


def schema_delivery_block(schema: Mapping[str, Any], *, contract_version: str) -> str:
    canonical = canonical_json_text(schema)
    return (
        f"Canonical schema delivery contract: {SCHEMA_DELIVERY_CONTRACT_VERSION}\n"
        f"Stage contract version: {contract_version}\n"
        f"Canonical schema SHA-256: {schema_sha256(schema)}\n"
        f"Canonical JSON schema: {canonical}\n"
        "The schema is authoritative: preserve every required key, reject additional keys, use exact "
        "JSON types and enum values, and obey every array cardinality."
    )


def _schema_failure_receipt(
    schema: Mapping[str, Any],
    *,
    contract_version: str,
    path: str,
    observed: Any,
    error_kind: str,
    root_schema_sha256: str | None = None,
) -> dict[str, Any]:
    required = schema.get("required", []) if isinstance(schema.get("required"), list) else []
    observed_keys = sorted(observed) if isinstance(observed, Mapping) else []
    return {
        "contract_version": contract_version,
        "schema_sha256": root_schema_sha256 or schema_sha256(schema),
        "required_keys": sorted(str(item) for item in required),
        "observed_keys": [str(item) for item in observed_keys],
        "missing_keys": sorted(str(item) for item in set(required).difference(observed_keys)),
        "extra_keys": sorted(str(item) for item in set(observed_keys).difference(required)),
        "failed_path": path,
        "error_kind": error_kind,
    }


def validate_json_schema_contract(
    value: Any,
    schema: Mapping[str, Any],
    *,
    contract_version: str,
    path: str = "$",
    root_schema_sha256: str | None = None,
) -> None:
    """Validate the finite JSON-schema subset used by the two model stages."""

    expected_type = schema.get("type")
    root_digest = root_schema_sha256 or schema_sha256(schema)
    if expected_type == "object":
        if not isinstance(value, Mapping):
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="type",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} must be an object", receipt)
        required = set(schema.get("required", []))
        observed_keys = set(value)
        if observed_keys != required:
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="key_set",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} key set mismatch", receipt)
        properties = schema.get("properties", {})
        for key in sorted(required):
            validate_json_schema_contract(
                value[key],
                properties[key],
                contract_version=contract_version,
                path=f"{path}.{key}",
                root_schema_sha256=root_digest,
            )
        return
    if expected_type == "array":
        if not isinstance(value, list):
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="type",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} must be an array", receipt)
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if (isinstance(minimum, int) and len(value) < minimum) or (
            isinstance(maximum, int) and len(value) > maximum
        ):
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="cardinality",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} has invalid cardinality", receipt)
        item_schema = schema.get("items")
        if isinstance(item_schema, Mapping):
            for index, item in enumerate(value):
                validate_json_schema_contract(
                    item,
                    item_schema,
                    contract_version=contract_version,
                    path=f"{path}[{index}]",
                    root_schema_sha256=root_digest,
                )
        return
    if expected_type == "boolean" and not isinstance(value, bool):
        receipt = _schema_failure_receipt(
            schema, contract_version=contract_version, path=path, observed=value, error_kind="type",
            root_schema_sha256=root_digest,
        )
        raise SchemaContractError(f"{path} must be boolean", receipt)
    if expected_type == "string":
        if not isinstance(value, str):
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="type",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} must be a string", receipt)
        allowed = schema.get("enum")
        if isinstance(allowed, list) and value not in allowed:
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="enum",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} enum mismatch", receipt)
        maximum_length = schema.get("maxLength")
        if isinstance(maximum_length, int) and len(value) > maximum_length:
            receipt = _schema_failure_receipt(
                schema, contract_version=contract_version, path=path, observed=value, error_kind="max_length",
                root_schema_sha256=root_digest,
            )
            raise SchemaContractError(f"{path} exceeds maximum length", receipt)


def candidate_exact_set_receipt(
    coverage: Mapping[str, Any], model_state: Mapping[str, Any]
) -> dict[str, Any]:
    required = _candidate_ids(coverage)
    observed: list[str] = []
    for cause in model_state.get("material_root_causes", []):
        if not isinstance(cause, Mapping):
            continue
        if isinstance(cause.get("dimension"), str):
            observed.append(str(cause["dimension"]))
        else:
            affects = cause.get("affects", [])
            if isinstance(affects, list):
                observed.extend(str(item) for item in affects if isinstance(item, str))
    duplicates = sorted({item for item in observed if observed.count(item) > 1})
    required_set = set(required)
    observed_set = set(observed)
    return {
        "contract_version": CANDIDATE_EXACT_SET_CONTRACT_VERSION,
        "required_candidates": required,
        "observed_candidates": sorted(observed),
        "missing_candidates": sorted(required_set.difference(observed_set)),
        "extra_candidates": sorted(observed_set.difference(required_set)),
        "duplicate_candidates": duplicates,
    }


def validate_candidate_exact_set(coverage: Mapping[str, Any], model_state: Mapping[str, Any]) -> dict[str, Any]:
    receipt = candidate_exact_set_receipt(coverage, model_state)
    if any(receipt[key] for key in ("missing_candidates", "extra_candidates", "duplicate_candidates")):
        raise CandidateSetContractError(receipt)
    if len(receipt["observed_candidates"]) != len(receipt["required_candidates"]):
        raise CandidateSetContractError(receipt)
    return receipt


def validate_coverage(value: Mapping[str, Any]) -> dict[str, Any]:
    validate_json_schema_contract(
        value,
        COVERAGE_JSON_SCHEMA,
        contract_version=COVERAGE_CONTRACT_VERSION,
    )
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
    normalized: Mapping[str, Any] = value
    if value.get("coverage_contract_version") == COVERAGE_CONTRACT_VERSION:
        copy = deepcopy(dict(value))
        if isinstance(copy.get("root_cause_candidate_dimensions"), list):
            copy["root_cause_candidate_dimensions"] = _candidate_ids(copy)
        if isinstance(copy.get("dimensions"), list):
            order = {dimension: index for index, dimension in enumerate(COVERAGE_DIMENSIONS)}
            copy["dimensions"] = sorted(
                copy["dimensions"],
                key=lambda row: order.get(row.get("dimension"), len(order)) if isinstance(row, Mapping) else len(order),
            )
        for field in ("evidence_hold_codes", "submission_hold_codes"):
            if isinstance(copy.get(field), list):
                copy[field] = sorted(copy[field])
        normalized = copy
    payload = canonical_json_text(normalized)
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
    for cause in model_state["material_root_causes"]:
        affects = cause["affects"]
        if any(item not in COVERAGE_DIMENSIONS for item in affects):
            raise HarnessContractError("adjudication root cause references an unknown coverage dimension")
    validate_candidate_exact_set(coverage, model_state)
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
        "schema_delivery_contract_version": SCHEMA_DELIVERY_CONTRACT_VERSION,
        "dynamic_adjudication_schema_version": DYNAMIC_ADJUDICATION_SCHEMA_VERSION,
        "candidate_exact_set_contract_version": CANDIDATE_EXACT_SET_CONTRACT_VERSION,
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
