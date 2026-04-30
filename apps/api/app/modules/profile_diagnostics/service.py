from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisAuditLog
from app.modules.analysis.repository import AnalysisRepository
from app.modules.profile_diagnostics.calculator import (
    DiagnosticOutcome,
    DiagnosticThresholds,
    PatternOutcomeDiagnosticResult,
    ProfileDiagnosticCalculator,
    StrategyProfileDiagnosticResult,
)
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendation,
    CalibrationRecommendationStatus,
    DiagnosticRunStatus,
    DiagnosticScopeType,
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
    StrategyProfileDiagnosticRun,
)
from app.modules.profile_diagnostics.recommender import (
    CalibrationRecommendationDraft,
    ProfileCalibrationRecommender,
)
from app.modules.profile_diagnostics.repository import (
    OutcomeSignalRow,
    ProfileDiagnosticRepository,
)
from app.modules.profile_diagnostics.schemas import ProfileDiagnosticRunRequest
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.repository import StrategyProfileRepository


class ProfileDiagnosticService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ProfileDiagnosticRepository(session)
        self.strategy_profile_repository = StrategyProfileRepository(session)
        self.analysis_repository = AnalysisRepository(session)
        self.calculator = ProfileDiagnosticCalculator()
        self.recommender = ProfileCalibrationRecommender()

    async def run_workspace_diagnostics(
        self,
        payload: ProfileDiagnosticRunRequest,
    ) -> StrategyProfileDiagnosticRun:
        return await self.run_diagnostics(payload)

    async def run_strategy_profile_diagnostics(
        self,
        payload: ProfileDiagnosticRunRequest,
    ) -> StrategyProfileDiagnosticRun:
        return await self.run_diagnostics(payload)

    async def run_pattern_diagnostics(
        self,
        payload: ProfileDiagnosticRunRequest,
    ) -> StrategyProfileDiagnosticRun:
        return await self.run_diagnostics(payload)

    async def run_diagnostics(
        self,
        payload: ProfileDiagnosticRunRequest,
    ) -> StrategyProfileDiagnosticRun:
        minimum_sample_size = payload.minimum_sample_size or self.default_minimum_sample_size
        horizons = payload.horizons_minutes
        scope_type = diagnostic_scope_type(payload)
        run = await self.repository.create_run(
            StrategyProfileDiagnosticRun(
                workspace_id=payload.workspace_id,
                status=DiagnosticRunStatus.RUNNING.value,
                scope_type=scope_type.value,
                filters_json=payload.model_dump(
                    mode="json",
                    exclude={"workspace_id", "horizons_minutes", "minimum_sample_size"},
                ),
                horizons_json=horizons,
                minimum_sample_size=minimum_sample_size,
                started_at=datetime.now(UTC),
            )
        )
        rows: list[OutcomeSignalRow] = []
        try:
            rows = await self.repository.list_outcome_signal_rows(
                workspace_id=payload.workspace_id,
                horizons_minutes=horizons,
                strategy_profile_key=payload.strategy_profile_key,
                symbol_id=payload.symbol_id,
                timeframe=payload.timeframe,
                pattern_type=payload.pattern_type,
                start_time=payload.start_time,
                end_time=payload.end_time,
                limit=payload.limit,
            )
            await self.add_audit_logs(
                rows=rows,
                event_type="profile_diagnostics_started",
                message="Profile diagnostics started",
                metadata_json={"diagnosticRunId": str(run.id), "outcomeCount": len(rows)},
            )
            diagnostic_outcomes = [diagnostic_outcome_from_row(row) for row in rows]
            thresholds = self.thresholds
            profile_results = self.calculator.build_strategy_profile_diagnostics(
                workspace_id=payload.workspace_id,
                outcomes=diagnostic_outcomes,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            pattern_results = self.calculator.build_pattern_diagnostics(
                workspace_id=payload.workspace_id,
                outcomes=diagnostic_outcomes,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            profile_models = [
                profile_diagnostic_model(run.id, result) for result in profile_results
            ]
            pattern_models = [
                pattern_diagnostic_model(run.id, result) for result in pattern_results
            ]
            await self.repository.create_strategy_profile_diagnostics(profile_models)
            await self.repository.create_pattern_diagnostics(pattern_models)
            profiles = await self.load_strategy_profiles(profile_results)
            drafts = self.recommender.build_recommendations(
                profile_diagnostics=profile_results,
                pattern_diagnostics=pattern_results,
                profiles_by_key_version=profiles,
                minimum_sample_size=minimum_sample_size,
                thresholds=thresholds,
            )
            recommendation_models = [
                recommendation_model(
                    workspace_id=payload.workspace_id,
                    diagnostic_run_id=run.id,
                    draft=draft,
                )
                for draft in drafts
            ]
            await self.repository.create_recommendations(recommendation_models)
            run.evaluated_signal_count = len({row.outcome.signal_id for row in rows})
            run.evaluated_outcome_count = len(rows)
            run.diagnostics_created_count = len(profile_models) + len(pattern_models)
            run.recommendations_created_count = len(recommendation_models)
            run.completed_at = datetime.now(UTC)
            run.status = (
                DiagnosticRunStatus.COMPLETED_WITH_WARNINGS.value
                if any(result.sample_size < minimum_sample_size for result in profile_results)
                else DiagnosticRunStatus.COMPLETED.value
            )
            await self.repository.update_run(run)
            await self.add_audit_logs(
                rows=rows,
                event_type="profile_diagnostics_completed",
                message="Profile diagnostics completed",
                metadata_json={
                    "diagnosticRunId": str(run.id),
                    "diagnosticsCreatedCount": run.diagnostics_created_count,
                    "recommendationsCreatedCount": run.recommendations_created_count,
                },
            )
            if recommendation_models:
                await self.add_audit_logs(
                    rows=rows,
                    event_type="calibration_recommendation_created",
                    message="Calibration recommendation created",
                    metadata_json={
                        "diagnosticRunId": str(run.id),
                        "recommendationCount": len(recommendation_models),
                    },
                )
            await self.session.commit()
            return run
        except Exception as error:
            run.status = DiagnosticRunStatus.FAILED.value
            run.error_message = str(error)
            run.completed_at = datetime.now(UTC)
            await self.repository.update_run(run)
            await self.add_audit_logs(
                rows=rows,
                event_type="profile_diagnostics_failed",
                message="Profile diagnostics failed",
                metadata_json={"diagnosticRunId": str(run.id)},
            )
            await self.session.commit()
            raise

    async def get_diagnostic_run(self, run_id: UUID) -> StrategyProfileDiagnosticRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "profile_diagnostic_run_not_found", "Diagnostic run not found")
        return run

    async def list_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        horizon_minutes: int | None = None,
        diagnostic_label: str | None = None,
    ) -> list[StrategyProfileDiagnostic]:
        return await self.repository.list_strategy_profile_diagnostics(
            workspace_id=workspace_id,
            diagnostic_run_id=diagnostic_run_id,
            strategy_profile_key=strategy_profile_key,
            symbol_id=symbol_id,
            timeframe=timeframe,
            horizon_minutes=horizon_minutes,
            diagnostic_label=diagnostic_label,
            limit=limit,
            offset=offset,
        )

    async def list_pattern_diagnostics(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        horizon_minutes: int | None = None,
        diagnostic_label: str | None = None,
    ) -> list[PatternOutcomeDiagnostic]:
        return await self.repository.list_pattern_diagnostics(
            workspace_id=workspace_id,
            diagnostic_run_id=diagnostic_run_id,
            pattern_type=pattern_type,
            strategy_profile_key=strategy_profile_key,
            symbol_id=symbol_id,
            timeframe=timeframe,
            horizon_minutes=horizon_minutes,
            diagnostic_label=diagnostic_label,
            limit=limit,
            offset=offset,
        )

    async def list_calibration_recommendations(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        diagnostic_run_id: UUID | None = None,
        status: str | None = None,
        severity: str | None = None,
        recommendation_type: str | None = None,
        strategy_profile_key: str | None = None,
        pattern_type: str | None = None,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
    ) -> list[CalibrationRecommendation]:
        return await self.repository.list_recommendations(
            workspace_id=workspace_id,
            diagnostic_run_id=diagnostic_run_id,
            status=status,
            severity=severity,
            recommendation_type=recommendation_type,
            strategy_profile_key=strategy_profile_key,
            pattern_type=pattern_type,
            symbol_id=symbol_id,
            timeframe=timeframe,
            limit=limit,
            offset=offset,
        )

    async def update_recommendation_status(
        self,
        recommendation_id: UUID,
        status: CalibrationRecommendationStatus,
    ) -> CalibrationRecommendation:
        recommendation = await self.repository.get_recommendation(recommendation_id)
        if recommendation is None:
            raise AppError(
                404,
                "calibration_recommendation_not_found",
                "Calibration recommendation not found",
            )
        recommendation.status = status.value
        updated = await self.repository.update_recommendation(recommendation)
        await self.session.commit()
        return updated

    async def load_strategy_profiles(
        self,
        diagnostics: list[StrategyProfileDiagnosticResult],
    ) -> dict[tuple[str, str | None], StrategyProfile]:
        profiles: dict[tuple[str, str | None], StrategyProfile] = {}
        for diagnostic in diagnostics:
            key = (diagnostic.strategy_profile_key, diagnostic.strategy_profile_version)
            if key in profiles:
                continue
            profile = None
            if diagnostic.strategy_profile_version is not None:
                profile = await self.strategy_profile_repository.get_by_key_version(
                    diagnostic.strategy_profile_key,
                    diagnostic.strategy_profile_version,
                )
            if profile is None:
                profile = await self.strategy_profile_repository.get_by_key(
                    diagnostic.strategy_profile_key
                )
            if profile is not None:
                profiles[key] = profile
        return profiles

    async def add_audit_logs(
        self,
        rows: list[OutcomeSignalRow],
        event_type: str,
        message: str,
        metadata_json: dict[str, object],
    ) -> None:
        seen: set[UUID] = set()
        for row in rows[:50]:
            analysis_run_id = row.outcome.analysis_run_id
            if analysis_run_id in seen:
                continue
            seen.add(analysis_run_id)
            await self.analysis_repository.add_audit_log(
                AnalysisAuditLog(
                    analysis_run_id=analysis_run_id,
                    event_type=event_type,
                    message=message,
                    metadata_json=metadata_json,
                )
            )

    @property
    def default_minimum_sample_size(self) -> int:
        return self.settings.profile_diagnostics_minimum_sample_size

    @property
    def thresholds(self) -> DiagnosticThresholds:
        return DiagnosticThresholds(
            strong_follow_through_rate=self.settings.profile_diagnostics_strong_follow_through_rate,
            high_reversal_rate=self.settings.profile_diagnostics_high_reversal_rate,
            high_no_follow_through_rate=(
                self.settings.profile_diagnostics_high_no_follow_through_rate
            ),
            confidence_misalignment_threshold=(
                self.settings.profile_diagnostics_confidence_misalignment_threshold
            ),
        )


def diagnostic_scope_type(payload: ProfileDiagnosticRunRequest) -> DiagnosticScopeType:
    filter_count = sum(
        1
        for value in [
            payload.strategy_profile_key,
            payload.symbol_id,
            payload.timeframe,
            payload.pattern_type,
        ]
        if value is not None
    )
    if filter_count > 1:
        return DiagnosticScopeType.CUSTOM
    if payload.strategy_profile_key is not None:
        return DiagnosticScopeType.STRATEGY_PROFILE
    if payload.symbol_id is not None:
        return DiagnosticScopeType.SYMBOL
    if payload.timeframe is not None:
        return DiagnosticScopeType.TIMEFRAME
    if payload.pattern_type is not None:
        return DiagnosticScopeType.PATTERN
    return DiagnosticScopeType.WORKSPACE


def diagnostic_outcome_from_row(row: OutcomeSignalRow) -> DiagnosticOutcome:
    outcome = row.outcome
    return DiagnosticOutcome(
        signal_id=outcome.signal_id,
        strategy_profile_key=outcome.strategy_profile_key,
        strategy_profile_version=outcome.strategy_profile_version,
        pattern_type=outcome.pattern_type,
        symbol_id=outcome.symbol_id,
        timeframe=outcome.timeframe,
        horizon_minutes=outcome.horizon_minutes,
        bias=outcome.bias,
        classification_status=outcome.classification_status,
        evaluation_status=outcome.evaluation_status,
        outcome_label=outcome.outcome_label,
        confidence_score=row.confidence_score,
        candidate_strength=row.candidate_strength,
        max_favorable_move=outcome.max_favorable_move,
        max_adverse_move=outcome.max_adverse_move,
        net_move=outcome.net_move,
        max_favorable_pips=outcome.max_favorable_pips,
        max_adverse_pips=outcome.max_adverse_pips,
        net_pips=outcome.net_pips,
        max_favorable_ticks=outcome.max_favorable_ticks,
        max_adverse_ticks=outcome.max_adverse_ticks,
        net_ticks=outcome.net_ticks,
    )


def profile_diagnostic_model(
    diagnostic_run_id: UUID,
    result: StrategyProfileDiagnosticResult,
) -> StrategyProfileDiagnostic:
    return StrategyProfileDiagnostic(
        workspace_id=result.workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        strategy_profile_key=result.strategy_profile_key,
        strategy_profile_version=result.strategy_profile_version,
        symbol_id=result.symbol_id,
        timeframe=result.timeframe,
        horizon_minutes=result.horizon_minutes,
        sample_size=result.sample_size,
        evaluated_count=result.evaluated_count,
        continuation_count=result.continuation_count,
        partial_follow_through_count=result.partial_follow_through_count,
        no_follow_through_count=result.no_follow_through_count,
        reversal_count=result.reversal_count,
        insufficient_data_count=result.insufficient_data_count,
        continuation_rate=result.continuation_rate,
        reversal_rate=result.reversal_rate,
        no_follow_through_rate=result.no_follow_through_rate,
        average_confidence_score=result.average_confidence_score,
        average_max_favorable_move=result.average_max_favorable_move,
        average_max_adverse_move=result.average_max_adverse_move,
        average_net_move=result.average_net_move,
        average_max_favorable_pips=result.average_max_favorable_pips,
        average_max_adverse_pips=result.average_max_adverse_pips,
        average_net_pips=result.average_net_pips,
        average_max_favorable_ticks=result.average_max_favorable_ticks,
        average_max_adverse_ticks=result.average_max_adverse_ticks,
        average_net_ticks=result.average_net_ticks,
        confidence_alignment_score=result.confidence_alignment_score,
        diagnostic_label=result.diagnostic_label.value,
        diagnostic_summary=result.diagnostic_summary,
        metadata_json=result.metadata_json,
    )


def pattern_diagnostic_model(
    diagnostic_run_id: UUID,
    result: PatternOutcomeDiagnosticResult,
) -> PatternOutcomeDiagnostic:
    return PatternOutcomeDiagnostic(
        workspace_id=result.workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        pattern_type=result.pattern_type,
        strategy_profile_key=result.strategy_profile_key,
        symbol_id=result.symbol_id,
        timeframe=result.timeframe,
        horizon_minutes=result.horizon_minutes,
        sample_size=result.sample_size,
        evaluated_count=result.evaluated_count,
        continuation_rate=result.continuation_rate,
        reversal_rate=result.reversal_rate,
        no_follow_through_rate=result.no_follow_through_rate,
        average_confidence_score=result.average_confidence_score,
        confidence_alignment_score=result.confidence_alignment_score,
        diagnostic_label=result.diagnostic_label.value,
        diagnostic_summary=result.diagnostic_summary,
        metadata_json=result.metadata_json,
    )


def recommendation_model(
    workspace_id: UUID,
    diagnostic_run_id: UUID,
    draft: CalibrationRecommendationDraft,
) -> CalibrationRecommendation:
    return CalibrationRecommendation(
        workspace_id=workspace_id,
        diagnostic_run_id=diagnostic_run_id,
        recommendation_type=draft.recommendation_type.value,
        strategy_profile_key=draft.strategy_profile_key,
        strategy_profile_version=draft.strategy_profile_version,
        pattern_type=draft.pattern_type,
        symbol_id=draft.symbol_id,
        timeframe=draft.timeframe,
        horizon_minutes=draft.horizon_minutes,
        severity=draft.severity.value,
        status=draft.status.value,
        title=draft.title,
        rationale=draft.rationale,
        suggested_change_json=draft.suggested_change_json,
        evidence_json=draft.evidence_json,
    )
