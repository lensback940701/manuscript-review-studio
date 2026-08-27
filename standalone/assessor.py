"""Two-pass standalone closure orchestration with deterministic gates."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.closure_state import (
    ClosureStateError,
    EVIDENCE_HOLD_CODES,
    SUBMISSION_HOLD_CODES,
    decide_state,
    minimal_receipt,
    public_card,
)

from . import __version__
from .document_reader import DocumentContent, DocumentReadError, read_document
from .events import EventSink, RunPhase
from .harness import (
    ADJUDICATION_CONTRACT_VERSION,
    COVERAGE_CONTRACT_VERSION,
    COVERAGE_DIMENSIONS,
    COVERAGE_JSON_SCHEMA,
    ContextBudgetReceipt,
    HarnessContractError,
    IntakeReceipt,
    analyze_intake_structure,
    context_budget,
    coverage_is_complete,
    harness_receipt,
    validate_adjudication_binding,
    validate_coverage,
    validate_cross_stage_consistency,
)
from .localization import localize_closure_card
from .prompting import (
    ADJUDICATION_JSON_SCHEMA,
    build_adjudication_messages,
    build_coverage_messages,
)
from .providers import (
    ChatCompletionClient,
    CompletionResult,
    ProviderConfigurationError,
    ProviderRequestError,
    load_provider_config,
    provider_stage_timeout_seconds,
    validate_reasoning_option,
)


MODEL_KEYS = frozenset(
    {
        "material_root_causes",
        "evidence_hold_codes",
        "submission_hold_codes",
        "protected",
        "parked_opportunities",
        "lite_suggestions",
    }
)
ROOT_CAUSE_KEYS = frozenset(
    {
        "observed",
        "locatable",
        "dimension",
        "style_only",
        "hold_only",
        "verification_only",
        "expected_benefit_exceeds_risk",
        "scope",
    }
)


class ModelContractError(ValueError):
    """Raised when model output is not exactly one finite stage contract."""


@dataclass(frozen=True, slots=True)
class RunOptions:
    manuscript_path: Path
    provider: str = "deepseek"
    model: str | None = None
    reasoning_option: str | None = None
    output_language: str = "zh"
    manuscript_identity: str | None = None
    confirm_complete_current_manuscript: bool = False
    prior_receipt: Mapping[str, Any] | None = None
    timeout_seconds: float | None = None
    transient_retries: int = 2


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    closure_card: dict[str, Any]
    minimal_receipt: dict[str, Any]
    provider: str | None
    model: str | None
    reasoning_option: str | None
    api_called: bool
    usage: dict[str, int]
    usage_calls: tuple[dict[str, int], ...]
    attempts: int
    artifact_sha256: str
    semantic_content_sha256: str
    character_count: int
    thread_id: str
    harness: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "closure_card": self.closure_card,
            "minimal_receipt": self.minimal_receipt,
            "runtime": {
                "provider": self.provider,
                "model": self.model,
                "reasoning_option": self.reasoning_option,
                "api_called": self.api_called,
                "usage": self.usage,
                "usage_calls": [dict(item) for item in self.usage_calls],
                "core_call_count": len(self.usage_calls),
                "attempts": self.attempts,
                "thread_id": self.thread_id,
                "artifact_sha256": self.artifact_sha256,
                "semantic_content_sha256": self.semantic_content_sha256,
                "character_count": self.character_count,
                "standalone_version": __version__,
                "skill_version": "0.2.1",
                "harness": self.harness,
            },
        }


def parse_model_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or not lines[-1].strip().startswith("```"):
            raise ModelContractError("model response contains an incomplete Markdown fence")
        if lines[0].strip() not in {"```", "```json", "```JSON"}:
            raise ModelContractError("model response uses an unsupported Markdown fence")
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelContractError("model response is not one JSON object") from exc
    if not isinstance(value, dict):
        raise ModelContractError("model response must be a JSON object")
    return value


def _string_list(value: Any, field: str, *, maximum: int, max_length: int = 240) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ModelContractError(f"{field} must be a list with at most {maximum} items")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item.strip()) > max_length:
            raise ModelContractError(f"{field} must contain concise non-empty strings")
        result.append(item.strip())
    return result


def validate_model_state(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != MODEL_KEYS:
        missing = sorted(MODEL_KEYS.difference(value))
        extra = sorted(set(value).difference(MODEL_KEYS))
        raise ModelContractError(f"model state key set mismatch; missing={missing}; extra={extra}")
    causes = value["material_root_causes"]
    if not isinstance(causes, list) or len(causes) > len(COVERAGE_DIMENSIONS):
        raise ModelContractError("material_root_causes exceeds the finite coverage dimension set")
    clean_causes: list[dict[str, Any]] = []
    for cause in causes:
        if not isinstance(cause, dict) or set(cause) != ROOT_CAUSE_KEYS:
            raise ModelContractError("each material root cause must match the exact finite schema")
        for field in ROOT_CAUSE_KEYS - {"dimension", "scope"}:
            if not isinstance(cause[field], bool):
                raise ModelContractError(f"material root cause {field} must be boolean")
        dimension = cause["dimension"]
        if dimension not in COVERAGE_DIMENSIONS:
            raise ModelContractError("material root cause dimension must use the registered coverage set")
        if cause["scope"] not in {"local", "central"}:
            raise ModelContractError("material root cause scope must be local or central")
        clean_cause = {key: value for key, value in cause.items() if key != "dimension"}
        clean_causes.append({**clean_cause, "affects": [dimension]})
    evidence = _string_list(
        value["evidence_hold_codes"],
        "evidence_hold_codes",
        maximum=len(EVIDENCE_HOLD_CODES),
        max_length=80,
    )
    submission = _string_list(
        value["submission_hold_codes"],
        "submission_hold_codes",
        maximum=len(SUBMISSION_HOLD_CODES),
        max_length=80,
    )
    if any(code not in EVIDENCE_HOLD_CODES for code in evidence):
        raise ModelContractError("evidence_hold_codes contains an unknown code")
    if any(code not in SUBMISSION_HOLD_CODES for code in submission):
        raise ModelContractError("submission_hold_codes contains an unknown code")
    protected = _string_list(value["protected"], "protected", maximum=5)
    parked = _string_list(value["parked_opportunities"], "parked_opportunities", maximum=2)
    suggestions = value["lite_suggestions"]
    if not isinstance(suggestions, list) or len(suggestions) > 3:
        raise ModelContractError("lite_suggestions must contain at most three items")
    clean_suggestions: list[dict[str, str]] = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict) or set(suggestion) != {
            "Direction",
            "Why it matters",
            "What to protect",
        }:
            raise ModelContractError("each Lite suggestion must use the exact three-field schema")
        clean: dict[str, str] = {}
        for field, text in suggestion.items():
            if not isinstance(text, str) or not text.strip() or len(text.strip()) > 240:
                raise ModelContractError(f"Lite suggestion {field} must be concise non-empty text")
            clean[field] = text.strip()
        clean_suggestions.append(clean)
    return {
        "material_root_causes": clean_causes,
        "evidence_hold_codes": list(dict.fromkeys(evidence)),
        "submission_hold_codes": list(dict.fromkeys(submission)),
        "protected": protected,
        "parked_opportunities": parked,
        "lite_suggestions": clean_suggestions,
    }


def _validate_model_output_language(value: Mapping[str, Any], language: str) -> None:
    if language != "zh":
        return
    cjk = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
    strings: list[str] = [*value["protected"], *value["parked_opportunities"]]
    for suggestion in value["lite_suggestions"]:
        strings.extend(str(suggestion[field]) for field in ("Direction", "Why it matters", "What to protect"))
    if any(not cjk.search(item) for item in strings):
        raise ModelContractError("requested Chinese output contains a non-Chinese public text value")


def _aggregate_usage(usages: Sequence[Mapping[str, int]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for usage in usages:
        for key, value in usage.items():
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                result[key] = result.get(key, 0) + value
    return result


def _base_state(document: DocumentContent, options: RunOptions, intake: IntakeReceipt) -> dict[str, Any]:
    identity = (options.manuscript_identity or document.path.name).strip()
    complete = bool(options.confirm_complete_current_manuscript and intake.complete_structure)
    state: dict[str, Any] = {
        "manuscript_complete": complete,
        "current_identity_clear": bool(identity),
        "whole_manuscript_read": complete and document.critical_basis_available,
        "critical_basis_available": document.critical_basis_available and intake.complete_structure,
        "bounded_scope": not options.confirm_complete_current_manuscript,
        "current_manuscript_identity": identity,
        "current_artifact_sha256": document.artifact_sha256,
        "current_semantic_content_sha256": document.semantic_content_sha256,
        "material_root_causes": [],
        "evidence_hold_codes": [],
        "submission_hold_codes": list(document.submission_hold_codes),
        "protected": [],
        "parked_opportunities": [],
        "lite_suggestions": [],
        "invalidation_events": [],
        "artifact_only_drift_verified": False,
        "formal_tone": False,
        "rewrite_requested": False,
        "output_language": options.output_language,
    }
    if options.prior_receipt is not None:
        state["prior_receipt"] = dict(options.prior_receipt)
        for field in ("evidence_hold_codes", "submission_hold_codes"):
            previous = options.prior_receipt.get(field, [])
            if isinstance(previous, list):
                state[field] = list(dict.fromkeys([*state[field], *previous]))
    return state


def _finish(
    document: DocumentContent,
    state: dict[str, Any],
    sink: EventSink,
    *,
    provider: str | None,
    model: str | None,
    reasoning_option: str | None,
    usage_calls: Sequence[Mapping[str, int]] = (),
    attempts: int = 0,
    harness_state: Mapping[str, Any],
) -> AnalysisResult:
    decision = decide_state(state)
    card = localize_closure_card(public_card(state), state["output_language"])
    receipt = minimal_receipt(
        decision,
        state["current_manuscript_identity"],
        artifact_sha256=document.artifact_sha256,
        semantic_content_sha256=document.semantic_content_sha256,
    )
    safe_usage_calls = tuple(dict(item) for item in usage_calls)
    return AnalysisResult(
        closure_card=card,
        minimal_receipt=receipt,
        provider=provider,
        model=model,
        reasoning_option=reasoning_option,
        api_called=bool(safe_usage_calls),
        usage=_aggregate_usage(safe_usage_calls),
        usage_calls=safe_usage_calls,
        attempts=attempts,
        artifact_sha256=document.artifact_sha256,
        semantic_content_sha256=document.semantic_content_sha256,
        character_count=document.character_count,
        thread_id=sink.thread_id,
        harness=dict(harness_state),
    )


def _request_stage(
    client: ChatCompletionClient,
    messages: list[dict[str, str]],
    *,
    reasoning_option: str,
    schema: Mapping[str, Any],
    schema_name: str,
    budget: ContextBudgetReceipt,
) -> CompletionResult:
    if not budget.passed:
        raise HarnessContractError("model context budget cannot hold the complete stage input and output reserve")
    completion = client.complete(
        messages,
        reasoning_option=reasoning_option,
        json_mode=True,
        json_schema=schema,
        json_schema_name=schema_name,
        max_output_tokens=budget.requested_max_output_tokens,
    )
    if completion.finish_reason == "length":
        raise ModelContractError(f"provider truncated {schema_name} at its output limit")
    return completion


def analyze_manuscript(options: RunOptions, *, event_sink: EventSink | None = None) -> AnalysisResult:
    sink = event_sink or EventSink()
    sink.start()
    intake: IntakeReceipt | None = None
    budgets: list[ContextBudgetReceipt] = []
    coverage: dict[str, Any] | None = None
    usage_calls: list[dict[str, int]] = []
    attempts: list[tuple[str, int]] = []
    try:
        sink.transition(RunPhase.READING)
        item_id = sink.item_started("document_read", "Read immutable manuscript and validate structure")
        document = read_document(options.manuscript_path)
        intake = analyze_intake_structure(document.text)
        sink.item_completed(
            item_id,
            "document_read",
            character_count=document.character_count,
            artifact_sha256=document.artifact_sha256,
            semantic_content_sha256=document.semantic_content_sha256,
            intake_contract_version=intake.contract_version,
            complete_structure=intake.complete_structure,
            heading_count=intake.heading_count,
        )
        state = _base_state(document, options, intake)
        initial_harness = harness_receipt(intake, budgets)
        if not options.confirm_complete_current_manuscript or not state["critical_basis_available"]:
            sink.transition(RunPhase.VALIDATING)
            item_id = sink.item_started("intake_gate", "Return fail-closed UNASSESSED intake state")
            result = _finish(
                document,
                state,
                sink,
                provider=None,
                model=None,
                reasoning_option=None,
                harness_state=initial_harness,
            )
            sink.item_completed(item_id, "intake_gate", verdict="UNASSESSED")
            sink.complete(verdict="UNASSESSED", usage={})
            return result
        if options.prior_receipt is not None:
            prior_decision = decide_state(state)
            if prior_decision["prior_receipt_valid"]:
                sink.transition(RunPhase.VALIDATING)
                item_id = sink.item_started("receipt_reuse", "Reuse stable prior closure receipt")
                result = _finish(
                    document,
                    state,
                    sink,
                    provider=None,
                    model=None,
                    reasoning_option=None,
                    harness_state=initial_harness,
                )
                sink.item_completed(item_id, "receipt_reuse", verdict=result.closure_card["Verdict"])
                sink.complete(verdict=result.closure_card["Verdict"], usage={})
                return result

        config = load_provider_config(options.provider, model=options.model)
        reasoning_option = validate_reasoning_option(config.name, config.model, options.reasoning_option)
        sink.transition(RunPhase.REQUESTING_MODEL)
        current_stage = "coverage"
        current_timeout = provider_stage_timeout_seconds(
            config.name,
            current_stage,
            override=options.timeout_seconds,
        )

        def on_attempt(number: int) -> None:
            attempts.append((current_stage, number))
            sink.emit(
                "provider.attempt",
                phase=sink.phase.value,
                stage=current_stage,
                provider=config.name,
                model=config.model,
                reasoning_option=reasoning_option,
                attempt=number,
                timeout_seconds=current_timeout,
            )

        coverage_client = ChatCompletionClient(
            config,
            timeout_seconds=current_timeout,
            max_transient_retries=options.transient_retries,
            on_attempt=on_attempt,
        )

        coverage_messages = build_coverage_messages(
            document.text,
            manuscript_identity=state["current_manuscript_identity"],
        )
        coverage_budget = context_budget(
            coverage_messages,
            provider=config.name,
            model=config.model,
        )
        budgets.append(coverage_budget)
        if not coverage_budget.passed:
            state["whole_manuscript_read"] = False
            sink.transition(RunPhase.VALIDATING)
            result = _finish(
                document,
                state,
                sink,
                provider=config.name,
                model=config.model,
                reasoning_option=reasoning_option,
                harness_state=harness_receipt(intake, budgets),
            )
            sink.complete(verdict="UNASSESSED", usage={})
            return result
        item_id = sink.item_started(
            "coverage_request",
            "Run whole-manuscript ten-dimension coverage pass",
            provider=config.name,
            model=config.model,
            reasoning_option=reasoning_option,
            estimated_input_tokens=coverage_budget.estimated_input_tokens,
            max_output_tokens=coverage_budget.requested_max_output_tokens,
            timeout_seconds=current_timeout,
        )
        coverage_completion = _request_stage(
            coverage_client,
            coverage_messages,
            reasoning_option=reasoning_option,
            schema=COVERAGE_JSON_SCHEMA,
            schema_name="mrc_whole_manuscript_coverage",
            budget=coverage_budget,
        )
        usage_calls.append(coverage_completion.usage)
        coverage = validate_coverage(parse_model_json(coverage_completion.content))
        coverage["submission_hold_codes"] = list(
            dict.fromkeys([*coverage["submission_hold_codes"], *document.submission_hold_codes])
        )
        sink.item_completed(
            item_id,
            "coverage_request",
            provider=config.name,
            model=coverage_completion.model,
            attempts=sum(1 for stage, _number in attempts if stage == "coverage"),
            usage=coverage_completion.usage,
            coverage_contract_version=COVERAGE_CONTRACT_VERSION,
            dimension_count=len(coverage["dimensions"]),
            coverage_complete=coverage_is_complete(coverage),
        )
        if not coverage_is_complete(coverage):
            state["whole_manuscript_read"] = False
            state["evidence_hold_codes"] = coverage["evidence_hold_codes"]
            state["submission_hold_codes"] = coverage["submission_hold_codes"]
            sink.transition(RunPhase.VALIDATING)
            result = _finish(
                document,
                state,
                sink,
                provider=config.name,
                model=coverage_completion.model,
                reasoning_option=reasoning_option,
                usage_calls=usage_calls,
                attempts=len(attempts),
                harness_state=harness_receipt(intake, budgets, coverage=coverage),
            )
            sink.complete(verdict="UNASSESSED", usage=result.usage)
            return result

        adjudication_messages = build_adjudication_messages(
            document.text,
            manuscript_identity=state["current_manuscript_identity"],
            output_language=options.output_language,
            coverage=coverage,
        )
        adjudication_budget = context_budget(
            adjudication_messages,
            provider=config.name,
            model=config.model,
        )
        budgets.append(adjudication_budget)
        if not adjudication_budget.passed:
            state["whole_manuscript_read"] = False
            sink.transition(RunPhase.VALIDATING)
            result = _finish(
                document,
                state,
                sink,
                provider=config.name,
                model=coverage_completion.model,
                reasoning_option=reasoning_option,
                usage_calls=usage_calls,
                attempts=len(attempts),
                harness_state=harness_receipt(intake, budgets, coverage=coverage),
            )
            sink.complete(verdict="UNASSESSED", usage=result.usage)
            return result

        current_stage = "adjudication"
        current_timeout = provider_stage_timeout_seconds(
            config.name,
            current_stage,
            override=options.timeout_seconds,
        )
        adjudication_client = ChatCompletionClient(
            config,
            timeout_seconds=current_timeout,
            max_transient_retries=options.transient_retries,
            on_attempt=on_attempt,
        )
        item_id = sink.item_started(
            "adjudication_request",
            "Re-read manuscript and adjudicate bound root-cause candidates",
            provider=config.name,
            model=config.model,
            reasoning_option=reasoning_option,
            estimated_input_tokens=adjudication_budget.estimated_input_tokens,
            max_output_tokens=adjudication_budget.requested_max_output_tokens,
            timeout_seconds=current_timeout,
        )
        adjudication_completion = _request_stage(
            adjudication_client,
            adjudication_messages,
            reasoning_option=reasoning_option,
            schema=ADJUDICATION_JSON_SCHEMA,
            schema_name="mrc_root_cause_adjudication",
            budget=adjudication_budget,
        )
        usage_calls.append(adjudication_completion.usage)
        envelope = parse_model_json(adjudication_completion.content)
        finite_state = validate_adjudication_binding(envelope, coverage)
        model_state = validate_model_state(finite_state)
        _validate_model_output_language(model_state, options.output_language)
        sink.item_completed(
            item_id,
            "adjudication_request",
            provider=config.name,
            model=adjudication_completion.model,
            attempts=sum(1 for stage, _number in attempts if stage == "adjudication"),
            usage=adjudication_completion.usage,
            adjudication_contract_version=ADJUDICATION_CONTRACT_VERSION,
            coverage_binding=True,
        )

        sink.transition(RunPhase.VALIDATING)
        item_id = sink.item_started(
            "contradiction_gate",
            "Independently verify cross-stage finite-state consistency",
        )
        validate_cross_stage_consistency(coverage, model_state)
        state.update(model_state)
        state["submission_hold_codes"] = list(
            dict.fromkeys([*model_state["submission_hold_codes"], *document.submission_hold_codes])
        )
        final_harness = harness_receipt(
            intake,
            budgets,
            coverage=coverage,
            adjudication_bound=True,
            contradiction_gate_passed=True,
        )
        result = _finish(
            document,
            state,
            sink,
            provider=config.name,
            model=adjudication_completion.model,
            reasoning_option=reasoning_option,
            usage_calls=usage_calls,
            attempts=len(attempts),
            harness_state=final_harness,
        )
        sink.item_completed(
            item_id,
            "contradiction_gate",
            verdict=result.closure_card["Verdict"],
            coverage_binding=True,
            contradiction_gate_passed=True,
        )
        sink.complete(verdict=result.closure_card["Verdict"], usage=result.usage)
        return result
    except (
        DocumentReadError,
        ProviderConfigurationError,
        ProviderRequestError,
        ModelContractError,
        HarnessContractError,
        ClosureStateError,
        RuntimeError,
    ) as exc:
        sink.fail(type(exc).__name__, str(exc))
        raise
