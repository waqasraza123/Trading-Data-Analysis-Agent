from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.explanations.repository import DeterministicExplanationRepository
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.llm_adapters.errors import LlmAdapterError, LlmProviderNotConfiguredError
from app.modules.llm_adapters.registry import LlmAdapterRegistry
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse
from app.modules.news.repository import NewsCorrelationRepository, NewsEventRepository
from app.modules.reasoning.grounding import check_reasoning_grounding
from app.modules.reasoning.input_builder import (
    ScenarioReasoningInputBuilder,
    build_news_correlation_payload,
)
from app.modules.reasoning.models import (
    LlmReasoningRun,
    ReasoningGroundingStatus,
    ReasoningRunStatus,
    ReasoningSafetyStatus,
    ReasoningSourceType,
    ReasoningType,
    ScenarioHypothesis,
    ScenarioPossibilityLabel,
    ScenarioType,
)
from app.modules.reasoning.parser import parse_scenario_reasoning_output
from app.modules.reasoning.prompt_builder import (
    PROMPT_VERSION,
    RESPONSE_SCHEMA_NAME,
    build_scenario_reasoning_prompts,
)
from app.modules.reasoning.repository import ScenarioReasoningRepository
from app.modules.reasoning.safety import check_reasoning_safety
from app.modules.reasoning.schemas import (
    ParsedScenarioReasoning,
    ReasoningRunRead,
    ScenarioItemRead,
    ScenarioOutput,
    ScenarioReasoningInputSnapshot,
    ScenarioReasoningResponse,
)
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository


class ScenarioReasoningService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.reasoning_repository = ScenarioReasoningRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.explanation_repository = DeterministicExplanationRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)
        self.news_correlation_repository = NewsCorrelationRepository(session)
        self.news_event_repository = NewsEventRepository(session)
        self.input_builder = ScenarioReasoningInputBuilder(session)
        self.adapter_registry = LlmAdapterRegistry(self.settings)

    async def build_signal_reasoning_input(
        self,
        signal_id: UUID,
    ) -> ScenarioReasoningInputSnapshot:
        signal = await self.load_signal(signal_id)
        run = await self.analysis_repository.get_run(signal.analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        symbol = await self.symbol_repository.get_by_id(signal.symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        confidence_components = await self.signal_repository.list_confidence_components(signal.id)
        evidence = await self.signal_repository.list_evidence(signal.id)
        risk_notes = await self.signal_repository.list_risk_notes(signal.id)
        deterministic_explanation = await self.explanation_repository.get_by_signal_id(signal.id)
        feature_snapshot = await self.feature_repository.get_by_analysis_run_id(run.id)
        indicator_snapshot = await self.indicator_repository.get_by_analysis_run_id(run.id)
        news_correlations = await self.build_news_correlation_input(signal.id)
        return await self.input_builder.build_signal_input(
            signal=signal,
            run=run,
            symbol=symbol,
            confidence_components=confidence_components,
            evidence=evidence,
            risk_notes=risk_notes,
            deterministic_explanation=deterministic_explanation,
            feature_snapshot=feature_snapshot,
            indicator_snapshot=indicator_snapshot,
            news_correlations=news_correlations,
            horizons_minutes=self.settings.outcome_default_horizons_minutes,
        )

    async def generate_signal_scenarios(
        self,
        signal_id: UUID,
        provider: str | None = None,
        model: str | None = None,
        force_recompute: bool = False,
    ) -> ScenarioReasoningResponse:
        signal = await self.load_signal(signal_id)
        provider_key = (provider or self.settings.llm_default_provider).strip().lower()
        model_name = (model or self.settings.llm_default_model).strip()
        if not force_recompute:
            existing = await self.reasoning_repository.get_latest_completed_signal_run(
                signal_id=signal.id,
                reasoning_type=ReasoningType.NEXT_SCENARIOS.value,
                provider=provider_key,
                model=model_name,
                prompt_version=PROMPT_VERSION,
            )
            if existing is not None:
                return await self.response_for_run(existing)
        input_snapshot = await self.build_signal_reasoning_input(signal.id)
        await self.add_audit_log(
            signal.analysis_run_id,
            "llm_reasoning_requested",
            "LLM scenario reasoning requested",
            {"signalId": str(signal.id), "provider": provider_key, "model": model_name},
        )
        await self.add_audit_log(
            signal.analysis_run_id,
            "llm_reasoning_input_built",
            "LLM scenario reasoning input built from persisted artifacts",
            {"signalId": str(signal.id), "promptVersion": PROMPT_VERSION},
        )
        run = await self.create_pending_run(signal, input_snapshot, provider_key, model_name)
        if not self.settings.llm_reasoning_enabled:
            await self.persist_fallback(
                run=run,
                parsed=fallback_disabled(),
                status=ReasoningRunStatus.PROVIDER_NOT_CONFIGURED,
                safety_status=ReasoningSafetyStatus.FALLBACK_USED,
                grounding_status=ReasoningGroundingStatus.NOT_CHECKED,
                error_message="llm_reasoning_disabled",
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_reasoning_failed",
                "LLM scenario reasoning skipped because reasoning is disabled",
                {"signalId": str(signal.id), "reason": "llm_reasoning_disabled"},
            )
            await self.session.commit()
            return await self.response_for_run(run)
        system_prompt, user_prompt = build_scenario_reasoning_prompts(input_snapshot)
        adapter_request = LlmAdapterRequest(
            provider=provider_key,
            model=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            input_json=input_snapshot.model_dump(mode="json", by_alias=True),
            response_schema_name=RESPONSE_SCHEMA_NAME,
            max_output_tokens=self.settings.llm_max_output_tokens,
            temperature=self.settings.llm_temperature,
            timeout_seconds=self.settings.llm_provider_timeout_seconds,
            metadata={
                "promptVersion": PROMPT_VERSION,
                "reasoningType": ReasoningType.NEXT_SCENARIOS.value,
            },
        )
        try:
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_reasoning_provider_started",
                "LLM scenario reasoning provider call started",
                {"signalId": str(signal.id), "provider": provider_key, "model": model_name},
            )
            adapter = self.adapter_registry.resolve(provider_key, model_name)
            adapter_response = await adapter.generate_structured(adapter_request)
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_reasoning_provider_completed",
                "LLM scenario reasoning provider call completed",
                {"signalId": str(signal.id), "provider": provider_key, "model": model_name},
            )
            await self.parse_and_persist_scenarios(run, adapter_response, input_snapshot)
        except LlmProviderNotConfiguredError as exc:
            await self.persist_fallback(
                run=run,
                parsed=fallback_provider_not_configured(),
                status=ReasoningRunStatus.PROVIDER_NOT_CONFIGURED,
                safety_status=ReasoningSafetyStatus.FALLBACK_USED,
                grounding_status=ReasoningGroundingStatus.NOT_CHECKED,
                error_message="provider_not_configured",
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_reasoning_failed",
                "LLM scenario reasoning provider was not configured",
                {"signalId": str(signal.id), "error": type(exc).__name__},
            )
        except LlmAdapterError as exc:
            await self.persist_fallback(
                run=run,
                parsed=fallback_provider_error(),
                status=ReasoningRunStatus.FALLBACK_USED,
                safety_status=ReasoningSafetyStatus.FAILED,
                grounding_status=ReasoningGroundingStatus.NOT_CHECKED,
                error_message="provider_error",
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_reasoning_failed",
                "LLM scenario reasoning provider failed",
                {"signalId": str(signal.id), "error": type(exc).__name__},
            )
        await self.session.commit()
        return await self.response_for_run(run)

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> ScenarioReasoningResponse:
        run = await self.reasoning_repository.get_run(reasoning_run_id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        return await self.response_for_run(run)

    async def get_signal_reasoning_runs(self, signal_id: UUID) -> list[ReasoningRunRead]:
        signal = await self.load_signal(signal_id)
        runs = await self.reasoning_repository.list_signal_runs(signal.id)
        return [ReasoningRunRead.model_validate(run) for run in runs]

    async def get_signal_latest_scenarios(self, signal_id: UUID) -> ScenarioReasoningResponse:
        signal = await self.load_signal(signal_id)
        run = await self.reasoning_repository.get_latest_signal_run(signal.id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        return await self.response_for_run(run)

    async def parse_and_persist_scenarios(
        self,
        reasoning_run: LlmReasoningRun,
        adapter_response: LlmAdapterResponse,
        input_snapshot: ScenarioReasoningInputSnapshot,
    ) -> None:
        parsed = parse_scenario_reasoning_output(adapter_response)
        output_json = parsed.model_dump(
            mode="json",
            by_alias=True,
            exclude={"fallback_used", "error_message"},
        )
        safety = check_reasoning_safety(adapter_response.output_text)
        if not safety.passed:
            await self.persist_fallback(
                run=reasoning_run,
                parsed=fallback_safety_blocked(),
                status=ReasoningRunStatus.BLOCKED,
                safety_status=ReasoningSafetyStatus.BLOCKED,
                grounding_status=ReasoningGroundingStatus.NOT_CHECKED,
                blocked_terms=safety.blocked_terms,
                tokens_input=adapter_response.tokens_input,
                tokens_output=adapter_response.tokens_output,
                estimated_cost=adapter_response.estimated_cost,
                latency_ms=adapter_response.latency_ms,
                error_message="safety_blocked",
            )
            await self.add_audit_log(
                reasoning_run.analysis_run_id,
                "llm_reasoning_safety_blocked",
                "LLM scenario reasoning output was blocked by safety validation",
                {"reasoningRunId": str(reasoning_run.id), "blockedTerms": safety.blocked_terms},
            )
            return
        if parsed.fallback_used:
            await self.persist_fallback(
                run=reasoning_run,
                parsed=parsed,
                status=ReasoningRunStatus.FALLBACK_USED,
                safety_status=ReasoningSafetyStatus.FALLBACK_USED,
                grounding_status=ReasoningGroundingStatus.NOT_CHECKED,
                tokens_input=adapter_response.tokens_input,
                tokens_output=adapter_response.tokens_output,
                estimated_cost=adapter_response.estimated_cost,
                latency_ms=adapter_response.latency_ms,
                error_message=parsed.error_message,
                output_text_override=adapter_response.output_text,
            )
            return
        grounding = check_reasoning_grounding(
            input_json=input_snapshot.model_dump(mode="json", by_alias=True),
            output_json=output_json,
            output_text=adapter_response.output_text,
        )
        if grounding.status == ReasoningGroundingStatus.FAILED:
            await self.persist_fallback(
                run=reasoning_run,
                parsed=fallback_grounding_failed(),
                status=ReasoningRunStatus.FALLBACK_USED,
                safety_status=ReasoningSafetyStatus.FALLBACK_USED,
                grounding_status=ReasoningGroundingStatus.FAILED,
                grounding_issues=grounding.issues,
                tokens_input=adapter_response.tokens_input,
                tokens_output=adapter_response.tokens_output,
                estimated_cost=adapter_response.estimated_cost,
                latency_ms=adapter_response.latency_ms,
                error_message="grounding_failed",
            )
            await self.add_audit_log(
                reasoning_run.analysis_run_id,
                "llm_reasoning_grounding_failed",
                "LLM scenario reasoning output failed grounding validation",
                {"reasoningRunId": str(reasoning_run.id), "groundingIssues": grounding.issues},
            )
            return
        reasoning_run.status = ReasoningRunStatus.COMPLETED.value
        reasoning_run.output_json = output_json if self.settings.llm_store_outputs else None
        reasoning_run.output_text = (
            adapter_response.output_text if self.settings.llm_store_outputs else None
        )
        reasoning_run.safety_status = ReasoningSafetyStatus.PASSED.value
        reasoning_run.grounding_status = grounding.status.value
        reasoning_run.blocked_terms_json = []
        reasoning_run.grounding_issues_json = grounding.issues
        reasoning_run.tokens_input = adapter_response.tokens_input
        reasoning_run.tokens_output = adapter_response.tokens_output
        reasoning_run.estimated_cost = adapter_response.estimated_cost
        reasoning_run.latency_ms = adapter_response.latency_ms
        reasoning_run.error_message = None
        await self.persist_scenarios(reasoning_run, parsed)
        await self.add_audit_log(
            reasoning_run.analysis_run_id,
            "llm_reasoning_completed",
            "LLM scenario reasoning completed",
            {"reasoningRunId": str(reasoning_run.id)},
        )

    async def persist_fallback(
        self,
        run: LlmReasoningRun,
        parsed: ParsedScenarioReasoning,
        status: ReasoningRunStatus,
        safety_status: ReasoningSafetyStatus,
        grounding_status: ReasoningGroundingStatus,
        blocked_terms: list[str] | None = None,
        grounding_issues: list[str] | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        estimated_cost: Decimal | None = None,
        latency_ms: int | None = None,
        error_message: str | None = None,
        output_text_override: str | None = None,
    ) -> None:
        run.status = status.value
        run.output_json = (
            parsed.model_dump(
                mode="json",
                by_alias=True,
                exclude={"fallback_used", "error_message"},
            )
            if self.settings.llm_store_outputs
            else None
        )
        run.output_text = (
            output_text_override or parsed.summary if self.settings.llm_store_outputs else None
        )
        run.safety_status = safety_status.value
        run.grounding_status = grounding_status.value
        run.blocked_terms_json = blocked_terms or []
        run.grounding_issues_json = grounding_issues or []
        run.tokens_input = tokens_input
        run.tokens_output = tokens_output
        run.estimated_cost = estimated_cost
        run.latency_ms = latency_ms
        run.error_message = error_message
        await self.persist_scenarios(run, parsed)

    async def persist_scenarios(
        self,
        run: LlmReasoningRun,
        parsed: ParsedScenarioReasoning,
    ) -> None:
        scenarios = [
            ScenarioHypothesis(
                id=uuid4(),
                reasoning_run_id=run.id,
                workspace_id=run.workspace_id,
                analysis_run_id=run.analysis_run_id,
                signal_id=run.signal_id,
                scenario_type=scenario.scenario_type.value,
                scenario_label=scenario.scenario_label,
                possibility_label=scenario.possibility_label.value,
                supporting_evidence_json=scenario.supporting_evidence,
                conflicting_evidence_json=scenario.conflicting_evidence,
                outcome_history_json=scenario.outcome_history,
                next_observations_json=scenario.next_observations,
                suggested_backend_actions_json=scenario.suggested_backend_actions,
                risk_notes_json=scenario.risk_notes,
                sort_order=index,
            )
            for index, scenario in enumerate(parsed.scenarios)
        ]
        await self.reasoning_repository.replace_scenarios(run.id, scenarios)
        await self.reasoning_repository.update_run(run)

    async def response_for_run(self, run: LlmReasoningRun) -> ScenarioReasoningResponse:
        scenarios = await self.reasoning_repository.list_scenarios(run.id)
        output_json = run.output_json or {}
        summary = output_json.get("summary")
        limitations = output_json.get("limitations")
        return ScenarioReasoningResponse(
            reasoning_run=ReasoningRunRead.model_validate(run),
            summary=summary if isinstance(summary, str) else (run.output_text or ""),
            scenarios=[
                ScenarioItemRead(
                    scenario_type=ScenarioType(scenario.scenario_type),
                    scenario_label=scenario.scenario_label,
                    possibility_label=ScenarioPossibilityLabel(scenario.possibility_label),
                    supporting_evidence=scenario.supporting_evidence_json,
                    conflicting_evidence=scenario.conflicting_evidence_json,
                    outcome_history=scenario.outcome_history_json,
                    next_observations=scenario.next_observations_json,
                    suggested_backend_actions=scenario.suggested_backend_actions_json,
                    risk_notes=scenario.risk_notes_json,
                )
                for scenario in scenarios
            ],
            limitations=limitations if isinstance(limitations, list) else [],
        )

    async def create_pending_run(
        self,
        signal: Signal,
        input_snapshot: ScenarioReasoningInputSnapshot,
        provider: str,
        model: str,
    ) -> LlmReasoningRun:
        run = LlmReasoningRun(
            id=uuid4(),
            workspace_id=signal.workspace_id,
            analysis_run_id=signal.analysis_run_id,
            signal_id=signal.id,
            outcome_id=None,
            source_type=ReasoningSourceType.SIGNAL.value,
            provider=provider,
            model=model,
            prompt_version=PROMPT_VERSION,
            reasoning_type=ReasoningType.NEXT_SCENARIOS.value,
            status=ReasoningRunStatus.PENDING.value,
            input_snapshot_json=(
                input_snapshot.model_dump(mode="json", by_alias=True)
                if self.settings.llm_store_inputs
                else {}
            ),
            output_json=None,
            output_text=None,
            safety_status=ReasoningSafetyStatus.FALLBACK_USED.value,
            grounding_status=ReasoningGroundingStatus.NOT_CHECKED.value,
            blocked_terms_json=[],
            grounding_issues_json=[],
        )
        return await self.reasoning_repository.create_run(run)

    async def build_news_correlation_input(self, signal_id: UUID) -> list[dict[str, object]]:
        correlations = await self.news_correlation_repository.list_by_signal_id(signal_id)
        events = await self.news_event_repository.get_many_by_ids(
            [correlation.news_event_id for correlation in correlations]
        )
        return build_news_correlation_payload(correlations, events)

    async def load_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def add_audit_log(
        self,
        analysis_run_id: UUID | None,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> AnalysisAuditLog | None:
        if analysis_run_id is None:
            return None
        return await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )


def fallback_disabled() -> ParsedScenarioReasoning:
    return fallback_response(
        "LLM scenario reasoning is disabled. Review deterministic artifacts directly.",
        "Reasoning layer disabled",
    )


def fallback_provider_not_configured() -> ParsedScenarioReasoning:
    return fallback_response(
        "The selected LLM provider is not configured. Review deterministic artifacts directly.",
        "Provider not configured",
    )


def fallback_provider_error() -> ParsedScenarioReasoning:
    return fallback_response(
        "The LLM provider failed. Review deterministic artifacts directly.",
        "Provider error",
    )


def fallback_safety_blocked() -> ParsedScenarioReasoning:
    return fallback_response(
        "The LLM output was blocked by safety validation. Review deterministic signal, evidence, "
        "risk notes, and outcomes directly.",
        "Safety validation blocked the output",
    )


def fallback_grounding_failed() -> ParsedScenarioReasoning:
    return fallback_response(
        "The LLM output was blocked by grounding validation. Review deterministic signal, "
        "evidence, risk notes, and outcomes directly.",
        "Grounding validation failed",
    )


def fallback_response(summary: str, limitation: str) -> ParsedScenarioReasoning:
    return ParsedScenarioReasoning(
        summary=summary,
        scenarios=[
            ScenarioOutput(
                scenario_type=ScenarioType.INSUFFICIENT_CONTEXT,
                scenario_label="Insufficient grounded scenario context",
                possibility_label=ScenarioPossibilityLabel.UNCERTAIN,
                supporting_evidence=[],
                conflicting_evidence=[],
                outcome_history={"available": False, "summary": "No grounded output available."},
                next_observations=["Review persisted deterministic artifacts directly."],
                suggested_backend_actions=["request_human_review"],
                risk_notes=[limitation],
            )
        ],
        limitations=[limitation],
        fallback_used=True,
        error_message=limitation,
    )
