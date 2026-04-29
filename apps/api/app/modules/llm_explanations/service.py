from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.explanations.models import DeterministicExplanation
from app.modules.explanations.repository import DeterministicExplanationRepository
from app.modules.explanations.templates import FALLBACK_EXPLANATION
from app.modules.features.repository import FeatureSnapshotRepository
from app.modules.indicators.repository import IndicatorSnapshotRepository
from app.modules.llm_explanations.grounding import check_explanation_grounding
from app.modules.llm_explanations.input_builder import build_llm_input_payload
from app.modules.llm_explanations.models import (
    LlmExplanation,
    LlmExplanationGroundingStatus,
    LlmExplanationSafetyStatus,
)
from app.modules.llm_explanations.prompt import PROMPT_VERSION, build_llm_prompt
from app.modules.llm_explanations.provider import (
    LlmExplanationInput,
    LlmProvider,
    LlmProviderError,
    LlmProviderResult,
    ProviderNotConfiguredError,
    build_provider,
)
from app.modules.llm_explanations.repository import LlmExplanationRepository
from app.modules.llm_explanations.safety import check_explanation_safety
from app.modules.llm_explanations.schemas import LlmExplanationInputPayload, LlmExplanationRead
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.news.repository import NewsCorrelationRepository, NewsEventRepository
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository


@dataclass(frozen=True)
class LlmValidationResult:
    output_text: str
    safety_status: LlmExplanationSafetyStatus
    grounding_status: LlmExplanationGroundingStatus
    blocked_terms: list[str]
    grounding_issues: list[str]


class LlmExplanationService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.llm_repository = LlmExplanationRepository(session)
        self.explanation_repository = DeterministicExplanationRepository(session)
        self.feature_repository = FeatureSnapshotRepository(session)
        self.indicator_repository = IndicatorSnapshotRepository(session)
        self.news_correlation_repository = NewsCorrelationRepository(session)
        self.news_event_repository = NewsEventRepository(session)

    async def generate_for_signal(
        self,
        signal_id: UUID,
        commit: bool = True,
        provider: LlmProvider | None = None,
    ) -> LlmExplanationRead:
        signal = await self.load_signal(signal_id)
        input_payload = await self.build_input_for_signal(signal.id)
        prompt = build_llm_prompt(input_payload)
        await self.add_audit_log(
            signal.analysis_run_id,
            "llm_explanation_requested",
            "LLM explanation generation requested",
            {"signalId": str(signal.id)},
        )
        await self.add_audit_log(
            signal.analysis_run_id,
            "llm_explanation_input_built",
            "LLM explanation input payload built from persisted artifacts",
            {
                "signalId": str(signal.id),
                "promptVersion": PROMPT_VERSION,
                "provider": self.settings.llm_provider,
                "model": self.settings.llm_model,
            },
        )
        deterministic_explanation = await self._get_deterministic_explanation(signal)
        fallback_text = self._safe_fallback_text(deterministic_explanation)

        if not self.settings.llm_explanations_enabled:
            validation = self._build_fallback_validation(fallback_text)
            persisted = await self.persist_result(signal, input_payload, validation)
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_fallback_used",
                "LLM explanation generation skipped because LLM explanations are disabled",
                {"signalId": str(signal.id), "reason": "disabled"},
            )
            if commit:
                await self.session.commit()
            return LlmExplanationRead.model_validate(persisted)

        if len(prompt.split()) > self.settings.llm_max_input_tokens:
            validation = self._build_provider_failure_validation(fallback_text)
            persisted = await self.persist_result(
                signal=signal,
                input_payload=input_payload,
                validation=validation,
                error_message="input_too_large",
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_failed",
                "LLM explanation input exceeded configured token budget",
                {"signalId": str(signal.id), "reason": "input_too_large"},
            )
            await self.emit_validation_audit(signal, validation)
            if commit:
                await self.session.commit()
            return LlmExplanationRead.model_validate(persisted)

        provider_result: LlmProviderResult | None = None
        try:
            resolved_provider = provider or build_provider(self.settings)
            provider_result = await resolved_provider.generate_explanation(
                LlmExplanationInput(
                    prompt=prompt,
                    input_json=input_payload.model_dump(mode="json"),
                )
            )
            validation = self.validate_output(
                input_payload=input_payload,
                output_text=provider_result.output_text,
                fallback_text=fallback_text,
            )
            error_message = None
        except ProviderNotConfiguredError as exc:
            validation = self._build_provider_failure_validation(fallback_text)
            error_message = "provider_not_configured"
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_fallback_used",
                "LLM explanation provider was not configured, using deterministic fallback",
                {"signalId": str(signal.id), "reason": error_message},
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_failed",
                "LLM explanation provider was not configured",
                {"signalId": str(signal.id), "error": type(exc).__name__},
            )
        except LlmProviderError as exc:
            validation = self._build_provider_failure_validation(fallback_text)
            error_message = "provider_error"
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_fallback_used",
                "LLM explanation provider failed, using deterministic fallback",
                {"signalId": str(signal.id), "reason": error_message},
            )
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_failed",
                "LLM explanation provider failed",
                {"signalId": str(signal.id), "error": type(exc).__name__},
            )

        persisted = await self.persist_result(
            signal=signal,
            input_payload=input_payload,
            validation=validation,
            tokens_input=provider_result.tokens_input if provider_result is not None else None,
            tokens_output=provider_result.tokens_output if provider_result is not None else None,
            estimated_cost=(
                provider_result.estimated_cost if provider_result is not None else None
            ),
            error_message=error_message,
        )
        await self.emit_validation_audit(signal, validation)
        if commit:
            await self.session.commit()
        return LlmExplanationRead.model_validate(persisted)

    async def get_for_signal(self, signal_id: UUID) -> LlmExplanationRead:
        signal = await self.load_signal(signal_id)
        explanation = await self.llm_repository.get_by_signal_id(signal.id)
        if explanation is None:
            raise AppError(404, "llm_explanation_not_found", "LLM explanation not found")
        return LlmExplanationRead.model_validate(explanation)

    async def get_for_analysis_run_id(self, analysis_run_id: UUID) -> LlmExplanationRead:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        explanation = await self.llm_repository.get_by_analysis_run_id(run.id)
        if explanation is None:
            raise AppError(404, "llm_explanation_not_found", "LLM explanation not found")
        return LlmExplanationRead.model_validate(explanation)

    async def generate_for_analysis_run_id(
        self,
        analysis_run_id: UUID,
        commit: bool = True,
        provider: LlmProvider | None = None,
    ) -> LlmExplanationRead:
        run = await self.analysis_repository.get_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.signal_repository.get_by_analysis_run_id(run.id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.generate_for_signal(signal.id, commit=commit, provider=provider)

    async def build_input_for_signal(self, signal_id: UUID) -> LlmExplanationInputPayload:
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
        deterministic_explanation = await self._get_deterministic_explanation(signal)
        feature_snapshot = await self.feature_repository.get_by_analysis_run_id(run.id)
        indicator_snapshot = await self.indicator_repository.get_by_analysis_run_id(run.id)
        news_correlations = await self.build_news_correlation_input(signal.id)
        return build_llm_input_payload(
            signal=signal,
            run=run,
            symbol=symbol.symbol,
            confidence_components=confidence_components,
            evidence=evidence,
            risk_notes=risk_notes,
            deterministic_explanation=deterministic_explanation,
            feature_snapshot=feature_snapshot,
            indicator_snapshot=indicator_snapshot,
            news_correlations=news_correlations,
        )

    async def build_news_correlation_input(self, signal_id: UUID) -> list[dict[str, object]]:
        correlations = await self.news_correlation_repository.list_by_signal_id(signal_id)
        events = await self.news_event_repository.get_many_by_ids(
            [correlation.news_event_id for correlation in correlations]
        )
        events_by_id = {event.id: event for event in events}
        safe_items: list[dict[str, object]] = []
        for correlation in correlations:
            event = events_by_id.get(correlation.news_event_id)
            if event is None:
                continue
            safe_items.append(self.serialize_news_correlation(correlation, event))
        return safe_items

    def serialize_news_correlation(
        self,
        correlation: SignalNewsCorrelation,
        event: NewsEvent,
    ) -> dict[str, object]:
        return {
            "eventTitle": event.title,
            "eventType": event.event_type,
            "eventTime": event.event_time.isoformat(),
            "currency": event.currency,
            "asset": event.asset,
            "importance": event.importance,
            "correlationLabel": correlation.correlation_label,
            "correlationScore": str(correlation.correlation_score),
            "timeDeltaMinutes": str(correlation.time_delta_minutes),
            "directionAlignment": correlation.direction_alignment,
            "volatilityReaction": correlation.volatility_reaction,
            "reason": correlation.reason,
        }

    def validate_output(
        self,
        input_payload: LlmExplanationInputPayload,
        output_text: str,
        fallback_text: str,
    ) -> LlmValidationResult:
        safety_result = check_explanation_safety(output_text)
        if not safety_result.passed:
            return LlmValidationResult(
                output_text=fallback_text,
                safety_status=LlmExplanationSafetyStatus.BLOCKED,
                grounding_status=LlmExplanationGroundingStatus.NOT_CHECKED,
                blocked_terms=safety_result.blocked_terms,
                grounding_issues=[],
            )
        grounding_result = check_explanation_grounding(
            input_json=input_payload.model_dump(mode="json"),
            output_text=output_text,
        )
        if grounding_result.status == LlmExplanationGroundingStatus.FAILED:
            return LlmValidationResult(
                output_text=fallback_text,
                safety_status=LlmExplanationSafetyStatus.FALLBACK_USED,
                grounding_status=grounding_result.status,
                blocked_terms=[],
                grounding_issues=grounding_result.issues,
            )
        return LlmValidationResult(
            output_text=output_text,
            safety_status=LlmExplanationSafetyStatus.PASSED,
            grounding_status=grounding_result.status,
            blocked_terms=[],
            grounding_issues=grounding_result.issues,
        )

    async def persist_result(
        self,
        signal: Signal,
        input_payload: LlmExplanationInputPayload,
        validation: LlmValidationResult,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        estimated_cost: Decimal | None = None,
        error_message: str | None = None,
    ) -> LlmExplanation:
        explanation = LlmExplanation(
            id=uuid4(),
            signal_id=signal.id,
            analysis_run_id=signal.analysis_run_id,
            workspace_id=signal.workspace_id,
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            prompt_version=PROMPT_VERSION,
            input_json=(
                input_payload.model_dump(mode="json") if self.settings.llm_store_inputs else {}
            ),
            output_text=validation.output_text,
            safety_status=validation.safety_status.value,
            blocked_terms_json=validation.blocked_terms,
            grounding_status=validation.grounding_status.value,
            grounding_issues_json=validation.grounding_issues,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            estimated_cost=estimated_cost,
            error_message=error_message,
        )
        try:
            return await self.llm_repository.upsert_for_signal(explanation)
        except IntegrityError as error:
            raise AppError(
                409,
                "llm_explanation_conflict",
                "LLM explanation could not be persisted",
            ) from error

    async def emit_validation_audit(
        self,
        signal: Signal,
        validation: LlmValidationResult,
    ) -> None:
        await self.add_audit_log(
            signal.analysis_run_id,
            "llm_explanation_generated",
            "LLM explanation generation completed with safe persisted output",
            {
                "signalId": str(signal.id),
                "provider": self.settings.llm_provider,
                "model": self.settings.llm_model,
                "safetyStatus": validation.safety_status.value,
                "groundingStatus": validation.grounding_status.value,
            },
        )
        if validation.safety_status == LlmExplanationSafetyStatus.BLOCKED:
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_blocked",
                "LLM explanation safety checker detected blocked terms",
                {"signalId": str(signal.id), "blockedTerms": validation.blocked_terms},
            )
        if validation.grounding_status == LlmExplanationGroundingStatus.FAILED:
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_grounding_failed",
                "LLM explanation grounding checker detected likely hallucination",
                {"signalId": str(signal.id), "groundingIssues": validation.grounding_issues},
            )
        if validation.safety_status in {
            LlmExplanationSafetyStatus.BLOCKED,
            LlmExplanationSafetyStatus.FALLBACK_USED,
            LlmExplanationSafetyStatus.FAILED,
        }:
            await self.add_audit_log(
                signal.analysis_run_id,
                "llm_explanation_fallback_used",
                "LLM explanation used deterministic fallback text",
                {"signalId": str(signal.id), "safetyStatus": validation.safety_status.value},
            )

    async def add_audit_log(
        self,
        analysis_run_id: UUID,
        event_type: str,
        message: str,
        metadata_json: dict[str, object] | None = None,
    ) -> AnalysisAuditLog:
        return await self.analysis_repository.add_audit_log(
            AnalysisAuditLog(
                analysis_run_id=analysis_run_id,
                event_type=event_type,
                message=message,
                metadata_json=metadata_json,
            )
        )

    async def load_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def _get_deterministic_explanation(
        self,
        signal: Signal,
    ) -> DeterministicExplanation | None:
        return await self.explanation_repository.get_by_signal_id(signal.id)

    def _safe_fallback_text(
        self,
        deterministic_explanation: DeterministicExplanation | None,
    ) -> str:
        if deterministic_explanation is None:
            return FALLBACK_EXPLANATION
        return deterministic_explanation.full_text

    def _build_fallback_validation(self, fallback_text: str) -> LlmValidationResult:
        return LlmValidationResult(
            output_text=fallback_text,
            safety_status=LlmExplanationSafetyStatus.FALLBACK_USED,
            grounding_status=LlmExplanationGroundingStatus.NOT_CHECKED,
            blocked_terms=[],
            grounding_issues=[],
        )

    def _build_provider_failure_validation(self, fallback_text: str) -> LlmValidationResult:
        return LlmValidationResult(
            output_text=fallback_text,
            safety_status=LlmExplanationSafetyStatus.FAILED,
            grounding_status=LlmExplanationGroundingStatus.NOT_CHECKED,
            blocked_terms=[],
            grounding_issues=[],
        )
