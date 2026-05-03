from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.models import AnalysisMode
from app.modules.intelligence_quality.gates import (
    FindingDraft,
    IntelligenceQualityGateService,
    score_findings,
    with_quality_run_artifact,
)
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    IntelligenceQualitySourceType,
    ShadowClassificationResult,
)
from app.modules.intelligence_quality.repository import (
    IntelligenceQualityArtifacts,
    IntelligenceQualityRepository,
)
from app.modules.intelligence_quality.schemas import (
    IntelligenceQualityFindingRead,
    IntelligenceQualityResponse,
    IntelligenceQualityRunRead,
    ShadowClassificationResultRead,
)
from app.modules.intelligence_quality.shadow import (
    SHADOW_CLASSIFICATION_DISABLED_VERSION,
    ShadowClassificationDraft,
    ShadowClassificationService,
)


class IntelligenceQualityService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = IntelligenceQualityRepository(session)
        self.gate_service = IntelligenceQualityGateService()
        self.shadow_service = ShadowClassificationService()

    async def run_for_signal(
        self,
        signal_id: UUID,
        include_shadow_classification: bool,
        force_recompute: bool,
    ) -> IntelligenceQualityResponse:
        shadow_version = self.shadow_version_for_request(include_shadow_classification)
        if not force_recompute:
            existing = await self.repository.get_latest_signal_run(
                signal_id=signal_id,
                gate_version=self.settings.intelligence_quality_gate_version,
                shadow_version=shadow_version,
            )
            if existing is not None:
                return await self.response_for_run(existing.id)
        artifacts = await self.repository.load_for_signal(signal_id)
        if artifacts.signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return await self.create_quality_run(
            artifacts=artifacts,
            source_type=IntelligenceQualitySourceType.SIGNAL.value,
            include_shadow_classification=include_shadow_classification,
            require_signal=True,
        )

    async def run_for_analysis_run(
        self,
        analysis_run_id: UUID,
        include_shadow_classification: bool,
        force_recompute: bool,
    ) -> IntelligenceQualityResponse:
        shadow_version = self.shadow_version_for_request(include_shadow_classification)
        if not force_recompute:
            existing = await self.repository.get_latest_analysis_run(
                analysis_run_id=analysis_run_id,
                gate_version=self.settings.intelligence_quality_gate_version,
                shadow_version=shadow_version,
            )
            if existing is not None:
                return await self.response_for_run(existing.id)
        artifacts = await self.repository.load_for_analysis_run(analysis_run_id)
        if artifacts.analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        source_type = (
            IntelligenceQualitySourceType.REPLAY.value
            if artifacts.analysis_run.analysis_mode == AnalysisMode.REPLAY.value
            else IntelligenceQualitySourceType.ANALYSIS_RUN.value
        )
        return await self.create_quality_run(
            artifacts=artifacts,
            source_type=source_type,
            include_shadow_classification=include_shadow_classification,
            require_signal=False,
        )

    async def get_latest_for_signal(
        self,
        signal_id: UUID,
        include_shadow_classification: bool = True,
    ) -> IntelligenceQualityResponse:
        run = await self.repository.get_latest_signal_run(
            signal_id=signal_id,
            gate_version=self.settings.intelligence_quality_gate_version,
            shadow_version=self.shadow_version_for_request(include_shadow_classification),
        )
        if run is None:
            raise AppError(404, "quality_run_not_found", "Quality run not found")
        return await self.response_for_run(run.id)

    async def get_latest_for_analysis_run(
        self,
        analysis_run_id: UUID,
        include_shadow_classification: bool = True,
    ) -> IntelligenceQualityResponse:
        run = await self.repository.get_latest_analysis_run(
            analysis_run_id=analysis_run_id,
            gate_version=self.settings.intelligence_quality_gate_version,
            shadow_version=self.shadow_version_for_request(include_shadow_classification),
        )
        if run is None:
            raise AppError(404, "quality_run_not_found", "Quality run not found")
        return await self.response_for_run(run.id)

    async def response_for_run(self, quality_run_id: UUID) -> IntelligenceQualityResponse:
        quality_run = await self.repository.get_run(quality_run_id)
        if quality_run is None:
            raise AppError(404, "quality_run_not_found", "Quality run not found")
        findings = await self.repository.list_findings(quality_run.id)
        shadow_results = await self.repository.list_shadow_results(quality_run.id)
        return IntelligenceQualityResponse(
            quality_run=IntelligenceQualityRunRead.model_validate(quality_run),
            findings=[IntelligenceQualityFindingRead.model_validate(item) for item in findings],
            shadow_classifications=[
                ShadowClassificationResultRead.model_validate(item) for item in shadow_results
            ],
        )

    async def list_findings(
        self,
        quality_run_id: UUID,
    ) -> list[IntelligenceQualityFindingRead]:
        await self.ensure_run_exists(quality_run_id)
        findings = await self.repository.list_findings(quality_run_id)
        return [IntelligenceQualityFindingRead.model_validate(item) for item in findings]

    async def list_shadow_classifications(
        self,
        quality_run_id: UUID,
    ) -> list[ShadowClassificationResultRead]:
        await self.ensure_run_exists(quality_run_id)
        results = await self.repository.list_shadow_results(quality_run_id)
        return [ShadowClassificationResultRead.model_validate(item) for item in results]

    async def create_quality_run(
        self,
        artifacts: IntelligenceQualityArtifacts,
        source_type: str,
        include_shadow_classification: bool,
        require_signal: bool,
    ) -> IntelligenceQualityResponse:
        try:
            gate_findings = self.gate_service.run_gates(artifacts, require_signal=require_signal)
            shadow_drafts: list[ShadowClassificationDraft] = []
            shadow_findings: list[FindingDraft] = []
            if include_shadow_classification:
                profiles = await self.repository.list_active_strategy_profiles()
                shadow_outcome = self.shadow_service.evaluate_profiles(artifacts, profiles)
                shadow_drafts = shadow_outcome.results
                shadow_findings = shadow_outcome.findings
            all_findings = gate_findings + shadow_findings
            score_result = score_findings(
                all_findings,
                strong_threshold=self.settings.intelligence_quality_strong_threshold,
                acceptable_threshold=self.settings.intelligence_quality_acceptable_threshold,
                review_threshold=self.settings.intelligence_quality_review_threshold,
            )
            run = await self.repository.create_quality_run(
                IntelligenceQualityRun(
                    workspace_id=self.workspace_id(artifacts),
                    analysis_run_id=(
                        artifacts.analysis_run.id
                        if artifacts.analysis_run is not None
                        else None
                    ),
                    signal_id=artifacts.signal.id if artifacts.signal is not None else None,
                    source_type=source_type,
                    status=score_result.status,
                    quality_score=score_result.quality_score,
                    quality_label=score_result.quality_label,
                    gate_version=self.settings.intelligence_quality_gate_version,
                    shadow_version=self.shadow_version_for_request(include_shadow_classification),
                    checked_at=utc_now(),
                    summary=score_result.summary,
                    metadata_json={
                        "deterministicOnly": True,
                        "signalMutation": False,
                        "profileMutation": False,
                        "shadowClassificationIncluded": include_shadow_classification,
                    },
                )
            )
            persisted_findings = await self.repository.create_findings(
                [
                    finding_model(self.workspace_id(artifacts), run.id, draft)
                    for draft in (
                        with_quality_run_artifact(draft, run.id) for draft in all_findings
                    )
                ]
            )
            persisted_shadow = await self.repository.create_shadow_results(
                [
                    shadow_result_model(run.id, draft)
                    for draft in shadow_drafts
                    if artifacts.analysis_run is not None
                ]
            )
            await self.session.commit()
            return IntelligenceQualityResponse(
                quality_run=IntelligenceQualityRunRead.model_validate(run),
                findings=[
                    IntelligenceQualityFindingRead.model_validate(item)
                    for item in persisted_findings
                ],
                shadow_classifications=[
                    ShadowClassificationResultRead.model_validate(item)
                    for item in persisted_shadow
                ],
            )
        except Exception:
            await self.session.rollback()
            raise

    def shadow_version_for_request(self, include_shadow_classification: bool) -> str:
        return shadow_version_for_request(include_shadow_classification, self.settings)

    async def ensure_run_exists(self, quality_run_id: UUID) -> IntelligenceQualityRun:
        run = await self.repository.get_run(quality_run_id)
        if run is None:
            raise AppError(404, "quality_run_not_found", "Quality run not found")
        return run

    def workspace_id(self, artifacts: IntelligenceQualityArtifacts) -> UUID:
        if artifacts.signal is not None:
            return artifacts.signal.workspace_id
        if artifacts.analysis_run is not None:
            return artifacts.analysis_run.workspace_id
        raise AppError(422, "quality_source_missing", "Quality source is missing workspace")


def shadow_version_for_request(
    include_shadow_classification: bool,
    settings: Settings | None = None,
) -> str:
    resolved_settings = settings or get_settings()
    return (
        resolved_settings.intelligence_quality_shadow_version
        if include_shadow_classification
        else SHADOW_CLASSIFICATION_DISABLED_VERSION
    )


def finding_model(
    workspace_id: UUID,
    quality_run_id: UUID,
    draft: FindingDraft,
) -> IntelligenceQualityFinding:
    return IntelligenceQualityFinding(
        workspace_id=workspace_id,
        quality_run_id=quality_run_id,
        finding_type=draft.finding_type,
        severity=draft.severity,
        code=draft.code,
        title=draft.title,
        message=draft.message,
        artifact_type=draft.artifact_type,
        artifact_id=draft.artifact_id,
        expected_value=draft.expected_value,
        observed_value=draft.observed_value,
        metadata_json=draft.metadata_json or {},
    )


def shadow_result_model(
    quality_run_id: UUID,
    draft: ShadowClassificationDraft,
) -> ShadowClassificationResult:
    return ShadowClassificationResult(
        workspace_id=draft.workspace_id,
        quality_run_id=quality_run_id,
        analysis_run_id=draft.analysis_run_id,
        signal_id=draft.signal_id,
        strategy_profile_key=draft.strategy_profile_key,
        strategy_profile_version=draft.strategy_profile_version,
        classification_status=draft.classification_status,
        bias=draft.bias,
        pattern_type=draft.pattern_type,
        confidence_score=draft.confidence_score,
        confidence_label=draft.confidence_label,
        selected_candidate_id=draft.selected_candidate_id,
        agreement_with_final=draft.agreement_with_final,
        disagreement_reason=draft.disagreement_reason,
        metadata_json=draft.metadata_json,
    )


def decimal_to_float(value: Decimal) -> float:
    return float(value)
