from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.ai_intelligence.grounding import check_ai_intelligence_grounding
from app.modules.ai_intelligence.input_builder import AiIntelligenceInputBuilder
from app.modules.ai_intelligence.models import (
    AiIntelligenceClaim,
    AiIntelligenceClaimSupportStatus,
    AiIntelligenceGroundingStatus,
    AiIntelligenceInsight,
    AiIntelligenceInsightType,
    AiIntelligenceRun,
    AiIntelligenceRunStatus,
    AiIntelligenceSafetyStatus,
    AiIntelligenceSeverity,
)
from app.modules.ai_intelligence.parser import parse_ai_intelligence_output
from app.modules.ai_intelligence.prompt import (
    PROMPT_VERSION,
    RESPONSE_SCHEMA_NAME,
    build_ai_intelligence_prompts,
)
from app.modules.ai_intelligence.repository import AiIntelligenceRepository
from app.modules.ai_intelligence.safety import check_ai_intelligence_safety
from app.modules.ai_intelligence.schemas import (
    AiArtifactRef,
    AiClaimOutput,
    AiInsightOutput,
    AiIntelligenceClaimRead,
    AiIntelligenceInputSnapshot,
    AiIntelligenceInsightRead,
    AiIntelligenceResponse,
    AiIntelligenceRunRead,
    ParsedAiIntelligence,
)
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.llm_adapters.errors import LlmAdapterError, LlmProviderNotConfiguredError
from app.modules.llm_adapters.registry import LlmAdapterRegistry
from app.modules.llm_adapters.schemas import LlmAdapterRequest, LlmAdapterResponse


class AiIntelligenceService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = AiIntelligenceRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.input_builder = AiIntelligenceInputBuilder(session)
        self.adapter_registry = LlmAdapterRegistry(self.settings)

    async def generate_signal_intelligence(
        self,
        signal_id: UUID,
        provider: str | None = None,
        model: str | None = None,
        force_recompute: bool = False,
    ) -> AiIntelligenceResponse:
        provider_key = (provider or self.settings.llm_default_provider).strip().lower()
        model_name = (model or self.settings.llm_default_model).strip()
        if not force_recompute:
            existing = await self.repository.get_latest_completed_signal_run(
                signal_id=signal_id,
                provider=provider_key,
                model=model_name,
                prompt_version=PROMPT_VERSION,
            )
            if existing is not None:
                return await self.response_for_run(existing)
        snapshot = await self.input_builder.build_signal_snapshot(signal_id)
        await self.add_audit_log(
            snapshot.analysis_run_id,
            "ai_intelligence_requested",
            "AI intelligence analysis requested",
            {"signalId": str(signal_id), "provider": provider_key, "model": model_name},
        )
        run = await self.create_pending_run(snapshot, provider_key, model_name)
        if not self.settings.ai_intelligence_enabled:
            await self.persist_fallback(
                run=run,
                parsed=fallback_disabled(snapshot.artifact_refs),
                status=AiIntelligenceRunStatus.PROVIDER_NOT_CONFIGURED,
                safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED,
                grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED,
                error_message="ai_intelligence_disabled",
            )
            await self.session.commit()
            return await self.response_for_run(run)
        system_prompt, user_prompt = build_ai_intelligence_prompts(snapshot)
        request = LlmAdapterRequest(
            provider=provider_key,
            model=model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            input_json=snapshot.model_dump(mode="json", by_alias=True),
            response_schema_name=RESPONSE_SCHEMA_NAME,
            max_output_tokens=self.settings.ai_intelligence_max_output_tokens,
            temperature=self.settings.llm_temperature,
            timeout_seconds=self.settings.llm_provider_timeout_seconds,
            metadata={"promptVersion": PROMPT_VERSION, "analysisType": "ai_intelligence"},
        )
        try:
            adapter = self.adapter_registry.resolve(provider_key, model_name)
            response = await adapter.generate_structured(request)
            await self.parse_and_persist(run, response, snapshot)
            await self.add_audit_log(
                snapshot.analysis_run_id,
                "ai_intelligence_completed",
                "AI intelligence analysis completed",
                {"aiIntelligenceRunId": str(run.id), "signalId": str(signal_id)},
            )
        except LlmProviderNotConfiguredError:
            await self.persist_fallback(
                run=run,
                parsed=fallback_provider_not_configured(snapshot.artifact_refs),
                status=AiIntelligenceRunStatus.PROVIDER_NOT_CONFIGURED,
                safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED,
                grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED,
                error_message="provider_not_configured",
            )
        except LlmAdapterError:
            await self.persist_fallback(
                run=run,
                parsed=fallback_provider_error(snapshot.artifact_refs),
                status=AiIntelligenceRunStatus.FALLBACK_USED,
                safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED,
                grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED,
                error_message="provider_error",
            )
        await self.session.commit()
        return await self.response_for_run(run)

    async def get_run(self, run_id: UUID) -> AiIntelligenceResponse:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "ai_intelligence_run_not_found", "AI intelligence run not found")
        return await self.response_for_run(run)

    async def list_signal_runs(
        self,
        signal_id: UUID,
        limit: int,
        offset: int,
    ) -> list[AiIntelligenceRunRead]:
        runs = await self.repository.list_signal_runs(signal_id, limit=limit, offset=offset)
        return [AiIntelligenceRunRead.model_validate(run) for run in runs]

    async def parse_and_persist(
        self,
        run: AiIntelligenceRun,
        response: LlmAdapterResponse,
        snapshot: AiIntelligenceInputSnapshot,
    ) -> None:
        parsed = parse_ai_intelligence_output(response)
        safety = check_ai_intelligence_safety(response.output_text)
        if not safety.passed:
            await self.persist_fallback(
                run=run,
                parsed=fallback_safety_blocked(snapshot.artifact_refs),
                status=AiIntelligenceRunStatus.BLOCKED,
                safety_status=AiIntelligenceSafetyStatus.BLOCKED,
                grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED,
                blocked_terms=safety.blocked_terms,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                error_message="safety_blocked",
            )
            return
        if parsed.fallback_used:
            await self.persist_fallback(
                run=run,
                parsed=parsed,
                status=AiIntelligenceRunStatus.FALLBACK_USED,
                safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED,
                grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                error_message=parsed.error_message,
            )
            return
        grounding = check_ai_intelligence_grounding(snapshot.artifact_refs, parsed)
        if grounding.status == AiIntelligenceGroundingStatus.FAILED:
            await self.persist_fallback(
                run=run,
                parsed=fallback_grounding_failed(snapshot.artifact_refs),
                status=AiIntelligenceRunStatus.FALLBACK_USED,
                safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED,
                grounding_status=AiIntelligenceGroundingStatus.FAILED,
                grounding_issues=grounding.issues,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                estimated_cost=response.estimated_cost,
                latency_ms=response.latency_ms,
                error_message="grounding_failed",
            )
            return
        await self.persist_completed(run, parsed, response, grounding.status)

    async def persist_completed(
        self,
        run: AiIntelligenceRun,
        parsed: ParsedAiIntelligence,
        response: LlmAdapterResponse,
        grounding_status: AiIntelligenceGroundingStatus,
    ) -> None:
        run.status = AiIntelligenceRunStatus.COMPLETED.value
        run.output_json = (
            parsed.model_dump(
                mode="json",
                by_alias=True,
                exclude={"fallback_used", "error_message"},
            )
            if self.settings.llm_store_outputs
            else None
        )
        run.output_text = response.output_text if self.settings.llm_store_outputs else None
        run.safety_status = AiIntelligenceSafetyStatus.PASSED.value
        run.grounding_status = grounding_status.value
        run.blocked_terms_json = []
        run.grounding_issues_json = []
        run.tokens_input = response.tokens_input
        run.tokens_output = response.tokens_output
        run.estimated_cost = response.estimated_cost
        run.latency_ms = response.latency_ms
        run.error_message = None
        run.completed_at = utc_now()
        await self.persist_insights_and_claims(run, parsed)
        await self.repository.update_run(run)

    async def persist_fallback(
        self,
        run: AiIntelligenceRun,
        parsed: ParsedAiIntelligence,
        status: AiIntelligenceRunStatus,
        safety_status: AiIntelligenceSafetyStatus,
        grounding_status: AiIntelligenceGroundingStatus,
        blocked_terms: list[str] | None = None,
        grounding_issues: list[str] | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        estimated_cost: Decimal | None = None,
        latency_ms: int | None = None,
        error_message: str | None = None,
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
        run.output_text = parsed.summary if self.settings.llm_store_outputs else None
        run.safety_status = safety_status.value
        run.grounding_status = grounding_status.value
        run.blocked_terms_json = blocked_terms or []
        run.grounding_issues_json = grounding_issues or []
        run.tokens_input = tokens_input
        run.tokens_output = tokens_output
        run.estimated_cost = estimated_cost
        run.latency_ms = latency_ms
        run.error_message = error_message
        run.completed_at = utc_now()
        await self.persist_insights_and_claims(run, parsed)
        await self.repository.update_run(run)

    async def persist_insights_and_claims(
        self,
        run: AiIntelligenceRun,
        parsed: ParsedAiIntelligence,
    ) -> None:
        insight_rows = [
            insight_row(run, insight, index)
            for index, insight in enumerate(parsed.insights)
        ]
        persisted_insights = await self.repository.replace_insights(run.id, insight_rows)
        claim_rows: list[AiIntelligenceClaim] = []
        for insight, persisted, insight_index in zip(
            parsed.insights,
            persisted_insights,
            range(len(persisted_insights)),
            strict=True,
        ):
            claim_rows.extend(claim_rows_for_insight(run, persisted.id, insight, insight_index))
        await self.repository.create_claims(claim_rows)

    async def create_pending_run(
        self,
        snapshot: AiIntelligenceInputSnapshot,
        provider: str,
        model: str,
    ) -> AiIntelligenceRun:
        run = AiIntelligenceRun(
            id=uuid4(),
            workspace_id=snapshot.workspace_id,
            subject_type=snapshot.subject_type.value,
            subject_id=snapshot.subject_id,
            signal_id=snapshot.signal_id,
            analysis_run_id=snapshot.analysis_run_id,
            outcome_id=snapshot.outcome_id,
            provider=provider,
            model=model,
            prompt_version=PROMPT_VERSION,
            status=AiIntelligenceRunStatus.PENDING.value,
            input_snapshot_json=(
                snapshot.model_dump(mode="json", by_alias=True)
                if self.settings.llm_store_inputs
                else {"artifactRefCount": len(snapshot.artifact_refs)}
            ),
            output_json=None,
            output_text=None,
            safety_status=AiIntelligenceSafetyStatus.FALLBACK_USED.value,
            grounding_status=AiIntelligenceGroundingStatus.NOT_CHECKED.value,
            blocked_terms_json=[],
            grounding_issues_json=[],
        )
        return await self.repository.create_run(run)

    async def response_for_run(self, run: AiIntelligenceRun) -> AiIntelligenceResponse:
        insights = await self.repository.list_insights(run.id)
        claims = await self.repository.list_claims(run.id)
        output_json = run.output_json or {}
        limitations = output_json.get("limitations")
        summary = output_json.get("summary")
        return AiIntelligenceResponse(
            run=AiIntelligenceRunRead.model_validate(run),
            summary=summary if isinstance(summary, str) else (run.output_text or ""),
            insights=[AiIntelligenceInsightRead.model_validate(item) for item in insights],
            claims=[AiIntelligenceClaimRead.model_validate(item) for item in claims],
            limitations=limitations if isinstance(limitations, list) else [],
        )

    async def add_audit_log(
        self,
        analysis_run_id: UUID | None,
        event_type: str,
        message: str,
        metadata_json: dict[str, object],
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


def insight_row(
    run: AiIntelligenceRun,
    insight: AiInsightOutput,
    sort_order: int,
) -> AiIntelligenceInsight:
    return AiIntelligenceInsight(
        id=uuid4(),
        run_id=run.id,
        workspace_id=run.workspace_id,
        insight_type=insight.insight_type.value,
        severity=insight.severity.value,
        title=insight.title,
        summary=insight.summary,
        rationale=insight.rationale,
        evidence_refs_json=refs_json(insight.evidence_refs),
        limitations_json=insight.limitations,
        safe_follow_up_actions_json=insight.safe_follow_up_actions,
        sort_order=sort_order,
    )


def claim_rows_for_insight(
    run: AiIntelligenceRun,
    insight_id: UUID,
    insight: AiInsightOutput,
    insight_index: int,
) -> list[AiIntelligenceClaim]:
    claims = insight.claims or [
        AiClaimOutput(
            claim=insight.summary,
            evidence_refs=insight.evidence_refs,
            support_status=AiIntelligenceClaimSupportStatus.SUPPORTED,
        )
    ]
    return [
        AiIntelligenceClaim(
            id=uuid4(),
            run_id=run.id,
            insight_id=insight_id,
            workspace_id=run.workspace_id,
            claim_text=claim.claim,
            support_status=claim.support_status.value,
            evidence_refs_json=refs_json(claim.evidence_refs),
            sort_order=(insight_index * 100) + claim_index,
        )
        for claim_index, claim in enumerate(claims)
    ]


def refs_json(refs: list[AiArtifactRef]) -> list[dict[str, object]]:
    return [ref.model_dump(mode="json", by_alias=True) for ref in refs]


def first_ref(refs: list[AiArtifactRef]) -> list[AiArtifactRef]:
    return refs[:1]


def fallback_disabled(refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    return fallback_response("AI intelligence is disabled.", refs)


def fallback_provider_not_configured(refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    return fallback_response("The selected AI intelligence provider is not configured.", refs)


def fallback_provider_error(refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    return fallback_response("The AI intelligence provider failed.", refs)


def fallback_safety_blocked(refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    return fallback_response("The AI intelligence output was blocked by safety validation.", refs)


def fallback_grounding_failed(refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    return fallback_response("The AI intelligence output failed citation grounding.", refs)


def fallback_response(message: str, refs: list[AiArtifactRef]) -> ParsedAiIntelligence:
    evidence_refs = first_ref(refs)
    return ParsedAiIntelligence(
        summary=message,
        insights=[
            AiInsightOutput(
                insight_type=AiIntelligenceInsightType.DATA_GAP,
                severity=AiIntelligenceSeverity.INFO,
                title="AI intelligence unavailable",
                summary="Review persisted deterministic artifacts directly.",
                rationale=message,
                evidence_refs=evidence_refs,
                limitations=[message],
                safe_follow_up_actions=["request_human_review"],
                claims=[
                    AiClaimOutput(
                        claim="No grounded AI intelligence insight was produced.",
                        evidence_refs=evidence_refs,
                    )
                ],
            )
        ],
        limitations=[message],
        fallback_used=True,
        error_message=message,
    )
