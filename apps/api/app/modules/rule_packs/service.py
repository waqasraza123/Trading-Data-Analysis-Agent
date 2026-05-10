from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisRun
from app.modules.analysis.repository import AnalysisRepository
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.engine_versions.registry import current_engine_snapshot
from app.modules.rule_packs.manifest import (
    build_candle_policy_snapshot,
    build_data_source_snapshot,
    build_manifest_summary,
    build_parser_snapshot,
    build_strategy_profile_snapshot,
    evaluate_replay_support,
    normalize_json_object,
)
from app.modules.rule_packs.models import (
    AnalysisReproducibilityManifest,
    RulePack,
    RulePackStatus,
)
from app.modules.rule_packs.repository import (
    ReproducibilityManifestRepository,
    RulePackRepository,
)
from app.modules.rule_packs.schemas import RulePackCreate
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.repository import StrategyProfileRepository
from app.modules.symbols.repository import SymbolRepository


class RulePackService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = RulePackRepository(session)
        self.strategy_profile_repository = StrategyProfileRepository(session)

    async def create_rule_pack(self, payload: RulePackCreate) -> RulePack:
        rule_pack = RulePack(
            workspace_id=payload.workspace_id,
            key=payload.key,
            name=payload.name,
            version=payload.version,
            status=payload.status.value,
            description=payload.description,
            engine_versions_json=normalize_json_object(payload.engine_versions_json),
            strategy_profile_refs_json=normalize_json_object(payload.strategy_profile_refs_json),
            parser_versions_json=normalize_json_object(payload.parser_versions_json),
            threshold_config_json=normalize_json_object(payload.threshold_config_json),
            module_versions_json=normalize_json_object(payload.module_versions_json),
            compatibility_json=normalize_json_object(payload.compatibility_json),
        )
        try:
            return await self.repository.create(rule_pack)
        except IntegrityError as error:
            raise AppError(
                409,
                "rule_pack_conflict",
                "Rule pack key and version already exist for this workspace scope",
            ) from error

    async def list_rule_packs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: RulePackStatus | None = None,
        key: str | None = None,
    ) -> list[RulePack]:
        return await self.repository.list_rule_packs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            key=key,
        )

    async def get_rule_pack(
        self,
        key: str,
        version: str,
        workspace_id: UUID | None = None,
    ) -> RulePack:
        rule_pack = await self.repository.get_by_key_version(
            key=key,
            version=version,
            workspace_id=workspace_id,
        )
        if rule_pack is None:
            raise AppError(404, "rule_pack_not_found", "Rule pack not found")
        return rule_pack

    async def seed_default_rule_pack(self, workspace_id: UUID | None = None) -> RulePack:
        existing = await self.repository.get_by_key_version(
            key=self.settings.rule_pack_default_key,
            version=self.settings.rule_pack_default_version,
            workspace_id=workspace_id,
            allow_global_fallback=False,
        )
        active_profiles = await self.strategy_profile_repository.list_active_profiles()
        payload = self.build_default_payload(active_profiles, workspace_id)
        if existing is None:
            return await self.repository.create(
                RulePack(
                    workspace_id=workspace_id,
                    key=payload.key,
                    name=payload.name,
                    version=payload.version,
                    status=payload.status.value,
                    description=payload.description,
                    engine_versions_json=payload.engine_versions_json,
                    strategy_profile_refs_json=payload.strategy_profile_refs_json,
                    parser_versions_json=payload.parser_versions_json,
                    threshold_config_json=payload.threshold_config_json,
                    module_versions_json=payload.module_versions_json,
                    compatibility_json=payload.compatibility_json,
                )
            )
        existing.name = payload.name
        existing.status = payload.status.value
        existing.description = payload.description
        existing.engine_versions_json = payload.engine_versions_json
        existing.strategy_profile_refs_json = payload.strategy_profile_refs_json
        existing.parser_versions_json = payload.parser_versions_json
        existing.threshold_config_json = payload.threshold_config_json
        existing.module_versions_json = payload.module_versions_json
        existing.compatibility_json = payload.compatibility_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    def build_default_payload(
        self,
        active_profiles: list[StrategyProfile],
        workspace_id: UUID | None,
    ) -> RulePackCreate:
        return RulePackCreate(
            workspace_id=workspace_id,
            key=self.settings.rule_pack_default_key,
            name="Core Deterministic Rule Pack",
            version=self.settings.rule_pack_default_version,
            status=RulePackStatus.ACTIVE,
            description=(
                "Default deterministic engine, strategy profile, parser, threshold, "
                "module, and compatibility registry."
            ),
            engine_versions_json=current_engine_snapshot(),
            strategy_profile_refs_json={
                "activeStrategyProfiles": [
                    strategy_profile_ref(profile) for profile in active_profiles
                ]
            },
            parser_versions_json=build_parser_versions(self.settings),
            threshold_config_json=build_threshold_config(self.settings, active_profiles),
            module_versions_json=build_module_versions(self.settings),
            compatibility_json={
                "replayCompatibilityPolicy": "current_registered_engine_versions",
                "missingOptionalModuleVersions": "unknown",
                "doesNotRunReplay": True,
                "doesNotMutateHistoricalOutputs": True,
            },
        )


class ReproducibilityManifestService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ReproducibilityManifestRepository(session)
        self.rule_pack_service = RulePackService(session, self.settings)
        self.analysis_repository = AnalysisRepository(session)
        self.signal_repository = SignalRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def generate_for_analysis_run(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> AnalysisReproducibilityManifest:
        analysis_run = await self.get_analysis_run(analysis_run_id)
        signal = await self.signal_repository.get_by_analysis_run_id(analysis_run.id)
        return await self.create_or_update_manifest(
            analysis_run=analysis_run,
            signal=signal,
            force_recompute=force_recompute,
        )

    async def generate_for_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> AnalysisReproducibilityManifest:
        signal = await self.get_signal(signal_id)
        analysis_run = await self.get_analysis_run(signal.analysis_run_id)
        return await self.create_or_update_manifest(
            analysis_run=analysis_run,
            signal=signal,
            force_recompute=force_recompute,
        )

    async def get_for_analysis_run(
        self,
        analysis_run_id: UUID,
    ) -> AnalysisReproducibilityManifest:
        manifest = await self.repository.get_by_analysis_run_version(
            analysis_run_id,
            self.settings.reproducibility_manifest_version,
        )
        if manifest is None:
            raise AppError(
                404,
                "reproducibility_manifest_not_found",
                "Reproducibility manifest not found",
            )
        return manifest

    async def get_for_signal(self, signal_id: UUID) -> AnalysisReproducibilityManifest:
        manifest = await self.repository.get_by_signal_version(
            signal_id,
            self.settings.reproducibility_manifest_version,
        )
        if manifest is not None:
            return manifest
        signal = await self.get_signal(signal_id)
        manifest = await self.repository.get_by_analysis_run_version(
            signal.analysis_run_id,
            self.settings.reproducibility_manifest_version,
        )
        if manifest is None or manifest.signal_id != signal.id:
            raise AppError(
                404,
                "reproducibility_manifest_not_found",
                "Reproducibility manifest not found",
            )
        return manifest

    async def create_or_update_manifest(
        self,
        analysis_run: AnalysisRun,
        signal: Signal | None,
        force_recompute: bool,
    ) -> AnalysisReproducibilityManifest:
        existing = await self.repository.get_by_analysis_run_version(
            analysis_run.id,
            self.settings.reproducibility_manifest_version,
        )
        if (
            existing is not None
            and not force_recompute
            and (signal is None or existing.signal_id == signal.id)
        ):
            return existing
        rule_pack = await self.rule_pack_service.seed_default_rule_pack(
            workspace_id=analysis_run.workspace_id
        )
        snapshot = await self.build_snapshot(analysis_run, signal, rule_pack)
        if existing is not None:
            existing.signal_id = signal.id if signal is not None else existing.signal_id
            existing.rule_pack_id = rule_pack.id
            existing.engine_snapshot_json = snapshot["engine"]
            existing.strategy_profile_snapshot_json = snapshot["strategyProfile"]
            existing.parser_snapshot_json = snapshot["parser"]
            existing.module_snapshot_json = snapshot["module"]
            existing.data_source_snapshot_json = snapshot["dataSource"]
            existing.candle_policy_snapshot_json = snapshot["candlePolicy"]
            existing.replay_support_status = str(snapshot["replaySupportStatus"])
            existing.summary = str(snapshot["summary"])
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        return await self.repository.create(
            AnalysisReproducibilityManifest(
                workspace_id=analysis_run.workspace_id,
                analysis_run_id=analysis_run.id,
                signal_id=signal.id if signal is not None else None,
                rule_pack_id=rule_pack.id,
                manifest_version=self.settings.reproducibility_manifest_version,
                engine_snapshot_json=snapshot["engine"],
                strategy_profile_snapshot_json=snapshot["strategyProfile"],
                parser_snapshot_json=snapshot["parser"],
                module_snapshot_json=snapshot["module"],
                data_source_snapshot_json=snapshot["dataSource"],
                candle_policy_snapshot_json=snapshot["candlePolicy"],
                replay_support_status=str(snapshot["replaySupportStatus"]),
                summary=str(snapshot["summary"]),
            )
        )

    async def build_snapshot(
        self,
        analysis_run: AnalysisRun,
        signal: Signal | None,
        rule_pack: RulePack,
    ) -> dict[str, Any]:
        symbol = await self.symbol_repository.get_by_id(analysis_run.symbol_id)
        data_source = (
            await self.data_source_repository.get_by_id(analysis_run.source_id)
            if analysis_run.source_id is not None
            else None
        )
        chart_runs = await self.list_chart_runs(analysis_run.id)
        engine_snapshot = normalize_json_object(
            analysis_run.engine_snapshot_json or {"status": "unknown"}
        )
        replay_support_status = evaluate_replay_support(engine_snapshot)
        return {
            "engine": engine_snapshot,
            "strategyProfile": build_strategy_profile_snapshot(analysis_run, signal),
            "parser": build_parser_snapshot(chart_runs),
            "module": {
                "rulePack": {
                    "id": str(rule_pack.id),
                    "key": rule_pack.key,
                    "version": rule_pack.version,
                    "status": rule_pack.status,
                },
                "ruleSetSnapshot": normalize_json_object(
                    analysis_run.rule_set_snapshot_json or {"status": "unknown"}
                ),
                "registeredModules": rule_pack.module_versions_json,
                "thresholdConfig": rule_pack.threshold_config_json,
            },
            "dataSource": build_data_source_snapshot(analysis_run, symbol, data_source),
            "candlePolicy": build_candle_policy_snapshot(analysis_run),
            "replaySupportStatus": replay_support_status.value,
            "summary": build_manifest_summary(analysis_run, signal, replay_support_status),
        }

    async def list_chart_runs(self, analysis_run_id: UUID) -> list[ChartScreenshotRun]:
        statement = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        analysis_run = await self.analysis_repository.get_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return analysis_run

    async def get_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal


def strategy_profile_ref(profile: StrategyProfile) -> dict[str, object]:
    return normalize_json_object(
        {
            "id": profile.id,
            "key": profile.key,
            "version": profile.version,
            "isActive": profile.is_active,
            "minimumCandidateStrength": profile.minimum_candidate_strength,
            "minimumConfidence": profile.minimum_confidence,
            "allowedPatterns": profile.allowed_patterns_json,
            "excludedPatterns": profile.excluded_patterns_json,
        }
    )


def build_parser_versions(settings: Settings) -> dict[str, object]:
    return {
        "chartScreenshotParser": {
            "version": "unknown",
            "status": "unknown",
            "optional": True,
        },
        "chartOcr": {
            "enabled": settings.chart_ocr_enabled,
            "provider": settings.chart_ocr_provider,
            "version": "unknown",
            "optional": True,
        },
    }


def build_threshold_config(
    settings: Settings,
    active_profiles: list[StrategyProfile],
) -> dict[str, object]:
    return normalize_json_object(
        {
            "strategyProfiles": [
                {
                    "key": profile.key,
                    "version": profile.version,
                    "minimumCandidateStrength": profile.minimum_candidate_strength,
                    "minimumConfidence": profile.minimum_confidence,
                    "componentWeights": profile.component_weights_json,
                    "riskFilters": profile.risk_filters_json,
                    "noSignalRules": profile.no_signal_rules_json,
                }
                for profile in active_profiles
            ],
            "chartScreenshot": {
                "ocrMinConfidence": settings.chart_ocr_min_confidence,
                "imageMinExtractionConfidence": settings.chart_image_min_extraction_confidence,
            },
            "outcomes": {
                "defaultHorizonsMinutes": settings.outcome_default_horizons_minutes,
                "minimumFutureCandles": settings.outcome_min_future_candles,
            },
        }
    )


def build_module_versions(settings: Settings) -> dict[str, object]:
    return {
        "outcomeEvaluation": {
            "version": settings.outcome_evaluation_version,
        },
        "profileDiagnostics": {
            "version": "unknown",
            "minimumSampleSize": settings.profile_diagnostics_minimum_sample_size,
            "strongFollowThroughRate": str(settings.profile_diagnostics_strong_follow_through_rate),
            "highReversalRate": str(settings.profile_diagnostics_high_reversal_rate),
            "highNoFollowThroughRate": str(
                settings.profile_diagnostics_high_no_follow_through_rate
            ),
            "confidenceMisalignmentThreshold": str(
                settings.profile_diagnostics_confidence_misalignment_threshold
            ),
        },
        "reasoning": {
            "enabled": settings.llm_reasoning_enabled,
            "provider": settings.llm_default_provider,
            "model": settings.llm_default_model,
            "version": "unknown",
        },
        "llmExplanations": {
            "enabled": settings.llm_explanations_enabled,
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "version": "unknown",
        },
        "intelligenceReports": {"version": "unknown"},
        "dataQuality": {"version": "unknown"},
    }
