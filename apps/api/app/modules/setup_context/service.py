from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.setup_context.builder import SetupContextArtifacts, SetupContextBuilder
from app.modules.setup_context.models import SetupContext
from app.modules.setup_context.repository import SetupContextRepository


class SetupContextService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = SetupContextRepository(session)
        self.builder = SetupContextBuilder(self.settings)

    async def build_for_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> SetupContext:
        try:
            signal = await self.repository.get_signal(signal_id)
            if signal is None:
                raise AppError(404, "signal_not_found", "Signal not found")
            existing = await self.repository.get_by_signal_version(
                signal_id=signal.id,
                context_version=self.settings.setup_context_version,
            )
            if existing is not None and not force_recompute:
                return existing
            analysis_run = await self.repository.get_analysis_run(signal.analysis_run_id)
            if analysis_run is None:
                raise AppError(404, "analysis_run_not_found", "Analysis run not found")
            artifacts = await self.build_artifacts(signal.id, analysis_run.id)
            setup_context = self.builder.build(artifacts)
            persisted = await self.repository.upsert(
                setup_context=setup_context,
                existing=existing,
                force_recompute=force_recompute,
            )
            await self.session.commit()
            await self.session.refresh(persisted)
            return persisted
        except AppError:
            await self.session.rollback()
            raise
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "setup_context_conflict",
                "Setup context could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def get_for_signal(self, signal_id: UUID) -> SetupContext:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        setup_context = await self.repository.get_latest_for_signal(signal_id)
        if setup_context is None:
            raise AppError(404, "setup_context_not_found", "Setup context not found")
        return setup_context

    async def build_for_analysis_run(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> SetupContext:
        analysis_run = await self.repository.get_analysis_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.repository.get_signal_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found for analysis run")
        return await self.build_for_signal(signal.id, force_recompute=force_recompute)

    async def get_for_analysis_run(self, analysis_run_id: UUID) -> SetupContext:
        analysis_run = await self.repository.get_analysis_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        setup_context = await self.repository.get_latest_for_analysis_run(analysis_run_id)
        if setup_context is None:
            raise AppError(404, "setup_context_not_found", "Setup context not found")
        return setup_context

    async def build_artifacts(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> SetupContextArtifacts:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        analysis_run = await self.repository.get_analysis_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        cross_asset_context_run = await self.repository.get_cross_asset_context_run(
            analysis_run_id=analysis_run.id,
            signal_id=signal.id,
        )
        return SetupContextArtifacts(
            signal=signal,
            analysis_run=analysis_run,
            confidence_components=await self.repository.list_confidence_components(signal.id),
            evidence=await self.repository.list_evidence(signal.id),
            risk_notes=await self.repository.list_risk_notes(signal.id),
            selected_pattern_candidate=await self.repository.get_selected_pattern_candidate(signal),
            recent_final_candles=await self.repository.list_recent_final_candles(analysis_run),
            feature_snapshot=await self.repository.get_feature_snapshot(analysis_run.id),
            advanced_feature_snapshot=await self.repository.get_advanced_feature_snapshot(
                analysis_run.id
            ),
            market_regime=await self.repository.get_market_regime(
                analysis_run_id=analysis_run.id,
                signal_id=signal.id,
            ),
            market_session=await self.repository.get_market_session(
                analysis_run_id=analysis_run.id,
                signal_id=signal.id,
            ),
            multi_timeframe_context=await self.repository.get_multi_timeframe_context(
                analysis_run_id=analysis_run.id,
                signal_id=signal.id,
            ),
            cross_asset_context_run=cross_asset_context_run,
            cross_asset_results=await self.repository.list_cross_asset_results(
                context_run_id=(
                    cross_asset_context_run.id if cross_asset_context_run is not None else None
                )
            ),
            outcomes=await self.repository.list_outcomes(signal.id),
            data_quality_run=await self.repository.get_latest_data_quality_run(analysis_run),
            decision_readiness=await self.repository.get_latest_decision_readiness(
                signal_id=signal.id,
                analysis_run_id=analysis_run.id,
            ),
        )
