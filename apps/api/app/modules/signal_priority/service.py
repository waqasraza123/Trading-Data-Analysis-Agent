from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.signal_priority.models import SignalPriorityScore
from app.modules.signal_priority.repository import SignalPriorityRepository
from app.modules.signal_priority.schemas import SignalPriorityListFilters
from app.modules.signal_priority.scorer import SignalPriorityScorer
from app.modules.workspaces.repository import WorkspaceRepository


class SignalPriorityService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = SignalPriorityRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.scorer = SignalPriorityScorer(self.settings)

    async def score_signal(
        self,
        signal_id: UUID,
        force_recompute: bool = False,
    ) -> SignalPriorityScore:
        try:
            signal = await self.repository.get_signal(signal_id)
            if signal is None:
                raise AppError(404, "signal_not_found", "Signal not found")
            existing = await self.repository.get_by_signal_version(
                signal_id=signal.id,
                priority_version=self.settings.signal_priority_version,
            )
            if existing is not None and not force_recompute:
                return existing
            artifacts = await self.repository.load_artifacts(
                signal=signal,
                quality_gate_version=self.settings.intelligence_quality_gate_version,
                shadow_version=self.settings.intelligence_quality_shadow_version,
                market_memory_version=self.settings.market_memory_state_version,
            )
            draft = self.scorer.score(artifacts)
            score = SignalPriorityScore(
                workspace_id=signal.workspace_id,
                signal_id=signal.id,
                analysis_run_id=signal.analysis_run_id,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                priority_version=self.settings.signal_priority_version,
                priority_score=draft.priority_score,
                priority_label=draft.priority_label.value,
                review_bucket=draft.review_bucket.value,
                component_scores_json=draft.component_scores_json,
                penalties_json=draft.penalties_json,
                boosters_json=draft.boosters_json,
                reasons_json=draft.reasons_json,
                warnings_json=draft.warnings_json,
            )
            persisted = await self.repository.upsert(
                score=score,
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
                "signal_priority_conflict",
                "Signal priority score could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def get_signal_priority(self, signal_id: UUID) -> SignalPriorityScore:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        score = await self.repository.get_latest_for_signal(signal_id)
        if score is None:
            raise AppError(404, "signal_priority_not_found", "Signal priority score not found")
        return score

    async def score_analysis_run_signal(
        self,
        analysis_run_id: UUID,
        force_recompute: bool = False,
    ) -> SignalPriorityScore:
        analysis_run = await self.repository.get_analysis_run(analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        signal = await self.repository.get_signal_by_analysis_run_id(analysis_run_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found for analysis run")
        return await self.score_signal(signal.id, force_recompute=force_recompute)

    async def list_prioritized_signals(
        self,
        filters: SignalPriorityListFilters,
    ) -> list[SignalPriorityScore]:
        await self.validate_workspace(filters.workspace_id)
        return await self.repository.list_priority_scores(
            workspace_id=filters.workspace_id,
            priority_label=(
                filters.priority_label.value if filters.priority_label is not None else None
            ),
            review_bucket=(
                filters.review_bucket.value if filters.review_bucket is not None else None
            ),
            symbol_id=filters.symbol_id,
            timeframe=filters.timeframe,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def score_workspace_recent_signals(
        self,
        workspace_id: UUID,
        limit: int = 500,
        force_recompute: bool = False,
    ) -> tuple[list[SignalPriorityScore], int]:
        await self.validate_workspace(workspace_id)
        signals = await self.repository.list_recent_signals(workspace_id, limit)
        scores: list[SignalPriorityScore] = []
        skipped_count = 0
        for signal in signals:
            try:
                scores.append(
                    await self.score_signal(
                        signal_id=signal.id,
                        force_recompute=force_recompute,
                    )
                )
            except AppError:
                skipped_count += 1
        return scores, skipped_count

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
