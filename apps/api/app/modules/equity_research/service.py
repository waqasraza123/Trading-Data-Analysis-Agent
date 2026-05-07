from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.analysis.models import AnalysisRunStatus
from app.modules.analysis.schemas import LiveWindowAnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.timeframes import Timeframe
from app.modules.equity_research.models import (
    EquityCatalystContext,
    EquitySwingCandidate,
    EquitySwingCandidateStatus,
    EquitySwingScanRun,
    EquitySwingScanRunStatus,
    EquityUniverse,
    EquityUniverseMember,
    EquityUniverseStatus,
)
from app.modules.equity_research.repository import EquityResearchArtifacts, EquityResearchRepository
from app.modules.equity_research.scanner import EquitySwingScanTarget
from app.modules.equity_research.schemas import (
    EquityCatalystContextCreate,
    EquitySwingScanCreate,
    EquityUniverseCreate,
    EquityUniverseMemberCreate,
    EquityUniverseMembersBulkCreate,
    EquityUniverseUpdate,
)
from app.modules.equity_research.scoring import (
    SCAN_PROFILES,
    EquitySwingScoreDraft,
    EquitySwingScorer,
    EquitySwingScoringInput,
)
from app.modules.equity_research.universe import ensure_universe_can_change
from app.modules.market_scans.models import MarketWatchlistStatus
from app.modules.setup_context.service import SetupContextService
from app.modules.signal_priority.service import SignalPriorityService
from app.modules.symbols.models import MarketType, Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.workspaces.repository import WorkspaceRepository


class EquityResearchService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: EquityResearchRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or EquityResearchRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.workspace_repository = WorkspaceRepository(session)
        self.analysis_service = AnalysisService(session)
        self.setup_context_service = SetupContextService(session, settings=self.settings)
        self.signal_priority_service = SignalPriorityService(session, settings=self.settings)
        self.scorer = EquitySwingScorer(self.settings)

    async def create_universe(self, payload: EquityUniverseCreate) -> EquityUniverse:
        await self.validate_workspace(payload.workspace_id)
        universe = EquityUniverse(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            status=EquityUniverseStatus.ACTIVE.value,
            universe_type=payload.universe_type.value,
            filters_json=payload.filters_json,
            metadata_json=payload.metadata_json,
        )
        try:
            created = await self.repository.create_universe(universe)
            await self.session.commit()
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "equity_universe_conflict",
                "Equity universe could not be created",
            ) from error

    async def list_universes(
        self,
        workspace_id: UUID,
        status: EquityUniverseStatus | None,
        limit: int,
        offset: int,
    ) -> list[EquityUniverse]:
        await self.validate_workspace(workspace_id)
        return await self.repository.list_universes(
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            limit=limit,
            offset=offset,
        )

    async def get_universe(self, universe_id: UUID) -> EquityUniverse:
        universe = await self.repository.get_universe(universe_id)
        if universe is None:
            raise AppError(404, "equity_universe_not_found", "Equity universe not found")
        return universe

    async def update_universe(
        self,
        universe_id: UUID,
        payload: EquityUniverseUpdate,
    ) -> EquityUniverse:
        universe = await self.get_universe(universe_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        for field_name, field_value in updates.items():
            if hasattr(field_value, "value"):
                field_value = field_value.value
            setattr(universe, field_name, field_value)
        try:
            updated = await self.repository.update_universe(universe)
            await self.session.commit()
            return updated
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "equity_universe_conflict",
                "Equity universe could not be updated",
            ) from error

    async def archive_universe(self, universe_id: UUID) -> EquityUniverse:
        universe = await self.get_universe(universe_id)
        universe.status = EquityUniverseStatus.ARCHIVED.value
        updated = await self.repository.update_universe(universe)
        await self.session.commit()
        return updated

    async def add_universe_member(
        self,
        universe_id: UUID,
        payload: EquityUniverseMemberCreate,
    ) -> EquityUniverseMember:
        universe = await self.get_universe(universe_id)
        ensure_universe_can_change(universe)
        symbol = await self.validate_stock_symbol(payload.symbol_id)
        existing = await self.repository.get_member_by_universe_symbol(universe.id, symbol.id)
        if existing is not None:
            if not existing.is_active:
                existing.is_active = True
                existing.average_volume = payload.average_volume
                existing.market_cap = payload.market_cap
                existing.metadata_json = payload.metadata_json
                updated = await self.repository.update_member(existing)
                await self.session.commit()
                return updated
            raise AppError(
                409,
                "equity_universe_member_exists",
                "Equity universe member already exists",
            )
        member = self.member_from_payload(universe, symbol, payload)
        try:
            created = await self.repository.create_member(member)
            await self.session.commit()
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "equity_universe_member_conflict",
                "Equity universe member could not be created",
            ) from error

    async def add_universe_members_bulk(
        self,
        universe_id: UUID,
        payload: EquityUniverseMembersBulkCreate,
    ) -> list[EquityUniverseMember]:
        created: list[EquityUniverseMember] = []
        for member_payload in payload.members:
            created.append(await self.add_universe_member(universe_id, member_payload))
        return created

    async def list_universe_members(
        self,
        universe_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[EquityUniverseMember]:
        await self.get_universe(universe_id)
        return await self.repository.list_members(
            universe_id=universe_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def remove_universe_member(
        self,
        universe_id: UUID,
        member_id: UUID,
    ) -> EquityUniverseMember:
        universe = await self.get_universe(universe_id)
        ensure_universe_can_change(universe)
        member = await self.repository.get_member(member_id)
        if member is None or member.universe_id != universe.id:
            raise AppError(404, "equity_universe_member_not_found", "Universe member not found")
        member.is_active = False
        updated = await self.repository.update_member(member)
        await self.session.commit()
        return updated

    async def run_swing_scan(self, payload: EquitySwingScanCreate) -> EquitySwingScanRun:
        await self.validate_workspace(payload.workspace_id)
        if payload.scan_profile_key not in SCAN_PROFILES:
            raise AppError(422, "equity_scan_profile_unknown", "Unknown equity scan profile")
        targets = await self.resolve_scan_targets(payload)
        if not targets:
            raise AppError(422, "equity_scan_no_targets", "No active stock symbols found")
        max_symbols = min(
            payload.filters.max_symbols or self.settings.equity_swing_scan_max_symbols,
            self.settings.equity_swing_scan_max_symbols,
        )
        targets = targets[:max_symbols]
        run = EquitySwingScanRun(
            workspace_id=payload.workspace_id,
            universe_id=payload.universe_id,
            watchlist_id=payload.watchlist_id,
            status=EquitySwingScanRunStatus.RUNNING.value,
            scan_version=self.settings.equity_research_version,
            scan_profile_key=payload.scan_profile_key,
            filters_json=payload.model_dump(mode="json", by_alias=True),
            scanned_symbol_count=0,
            candidate_count=0,
            rejected_count=0,
            summary="Equity swing research scan running",
        )
        created_run = await self.repository.create_scan_run(run)
        await self.session.commit()
        candidates: list[EquitySwingCandidate] = []
        try:
            for target in targets:
                analysis_run_id = await self.maybe_run_analysis(payload, target)
                artifacts = await self.repository.get_artifacts(
                    workspace_id=payload.workspace_id,
                    symbol_id=target.symbol_id,
                    timeframe=target.timeframe,
                    source_id=target.source_id or payload.filters.source_id,
                )
                if payload.options.generate_setup_context and artifacts.signal is not None:
                    setup_context = await self.setup_context_service.build_for_signal(
                        artifacts.signal.id
                    )
                    artifacts = await self.repository.get_artifacts(
                        payload.workspace_id,
                        target.symbol_id,
                        target.timeframe,
                        target.source_id or payload.filters.source_id,
                    )
                    analysis_run_id = setup_context.analysis_run_id
                if payload.options.score_signal_priority and artifacts.signal is not None:
                    await self.signal_priority_service.score_signal(artifacts.signal.id)
                candles = await self.repository.list_recent_final_candles(
                    workspace_id=payload.workspace_id,
                    symbol_id=target.symbol_id,
                    timeframe=target.timeframe,
                    source_id=target.source_id or payload.filters.source_id,
                    limit=candle_limit_for_timeframe(
                        target.timeframe,
                        self.settings.equity_swing_lookback_days,
                    ),
                )
                score = self.scorer.score(
                    EquitySwingScoringInput(
                        ticker=target.ticker,
                        timeframe=target.timeframe,
                        candles=candles,
                        artifacts=artifacts,
                        average_volume=target.average_volume,
                        min_average_volume=(
                            payload.filters.min_average_volume
                            or Decimal(self.settings.equity_swing_min_average_volume)
                        ),
                        min_setup_score=(
                            payload.filters.min_setup_score
                            or Decimal(self.settings.equity_swing_min_setup_score)
                        ),
                        strong_setup_score=Decimal(self.settings.equity_swing_strong_setup_score),
                        profile=self.scorer.profile(payload.scan_profile_key),
                        evaluated_at=datetime.now(UTC),
                        source_id_provided=target.source_id is not None
                        or payload.filters.source_id is not None,
                    )
                )
                candidates.append(
                    candidate_from_score(
                        run=created_run,
                        target=target,
                        score=score,
                        setup_context_id=setup_context_id_from_artifacts(artifacts),
                        signal_id=artifacts.signal.id if artifacts.signal is not None else None,
                        analysis_run_id=analysis_run_id_from_artifacts(
                            explicit_analysis_run_id=analysis_run_id,
                            artifacts_analysis_run_id=(
                                artifacts.analysis_run.id
                                if artifacts.analysis_run is not None
                                else None
                            ),
                        ),
                    )
                )
            await self.repository.create_candidates(candidates)
            created_run.scanned_symbol_count = len(
                {candidate.symbol_id for candidate in candidates}
            )
            created_run.candidate_count = sum(
                1
                for candidate in candidates
                if candidate.candidate_status
                in {
                    EquitySwingCandidateStatus.CANDIDATE.value,
                    EquitySwingCandidateStatus.NEEDS_CONFIRMATION.value,
                    EquitySwingCandidateStatus.CONFLICTED.value,
                }
            )
            created_run.rejected_count = len(candidates) - created_run.candidate_count
            created_run.status = (
                EquitySwingScanRunStatus.COMPLETED_WITH_WARNINGS.value
                if created_run.rejected_count
                else EquitySwingScanRunStatus.COMPLETED.value
            )
            created_run.completed_at = datetime.now(UTC)
            created_run.summary = (
                f"Equity swing research scan reviewed {created_run.scanned_symbol_count} "
                f"symbols and persisted {len(candidates)} deterministic scan results."
            )
            await self.repository.update_scan_run(created_run)
            await self.session.commit()
            return created_run
        except Exception as error:
            await self.session.rollback()
            failed = await self.repository.get_scan_run(created_run.id)
            if failed is not None:
                failed.status = EquitySwingScanRunStatus.FAILED.value
                failed.error_message = safe_error_message(error)
                failed.completed_at = datetime.now(UTC)
                failed.summary = "Equity swing research scan failed"
                await self.repository.update_scan_run(failed)
                await self.session.commit()
                return failed
            raise

    async def get_scan_run(self, scan_run_id: UUID) -> EquitySwingScanRun:
        run = await self.repository.get_scan_run(scan_run_id)
        if run is None:
            raise AppError(404, "equity_swing_scan_not_found", "Equity swing scan not found")
        return run

    async def list_scan_runs(
        self,
        workspace_id: UUID,
        status: EquitySwingScanRunStatus | None,
        universe_id: UUID | None,
        watchlist_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[EquitySwingScanRun]:
        await self.validate_workspace(workspace_id)
        return await self.repository.list_scan_runs(
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            universe_id=universe_id,
            watchlist_id=watchlist_id,
            limit=limit,
            offset=offset,
        )

    async def list_candidates(
        self,
        scan_run_id: UUID,
        limit: int,
        offset: int,
        candidate_status: EquitySwingCandidateStatus | None = None,
        setup_type: str | None = None,
        setup_quality_label: str | None = None,
    ) -> list[EquitySwingCandidate]:
        await self.get_scan_run(scan_run_id)
        return await self.repository.list_candidates(
            scan_run_id=scan_run_id,
            limit=limit,
            offset=offset,
            candidate_status=candidate_status.value if candidate_status is not None else None,
            setup_type=setup_type,
            setup_quality_label=setup_quality_label,
        )

    async def get_candidate(self, candidate_id: UUID) -> EquitySwingCandidate:
        candidate = await self.repository.get_candidate(candidate_id)
        if candidate is None:
            raise AppError(404, "equity_swing_candidate_not_found", "Candidate not found")
        return candidate

    async def create_catalyst(
        self,
        payload: EquityCatalystContextCreate,
    ) -> EquityCatalystContext:
        await self.validate_workspace(payload.workspace_id)
        await self.validate_stock_symbol(payload.symbol_id)
        catalyst = EquityCatalystContext(
            workspace_id=payload.workspace_id,
            symbol_id=payload.symbol_id,
            source_type=payload.source_type,
            event_time=payload.event_time,
            catalyst_type=payload.catalyst_type.value,
            title=payload.title,
            summary=payload.summary,
            importance=payload.importance.value,
            sentiment=payload.sentiment.value,
            raw_reference_json=payload.raw_reference_json,
        )
        created = await self.repository.create_catalyst(catalyst)
        await self.session.commit()
        return created

    async def list_catalysts(
        self,
        workspace_id: UUID,
        symbol_id: UUID | None,
        catalyst_type: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityCatalystContext]:
        await self.validate_workspace(workspace_id)
        if symbol_id is not None:
            await self.validate_stock_symbol(symbol_id)
        return await self.repository.list_catalysts(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            catalyst_type=catalyst_type,
            limit=limit,
            offset=offset,
        )

    async def resolve_scan_targets(
        self,
        payload: EquitySwingScanCreate,
    ) -> list[EquitySwingScanTarget]:
        timeframes = [timeframe.value for timeframe in payload.timeframes] or default_timeframes(
            self.settings.equity_swing_default_timeframes
        )
        if payload.universe_id is not None:
            universe = await self.get_universe(payload.universe_id)
            if universe.workspace_id != payload.workspace_id:
                raise AppError(
                    422,
                    "equity_universe_workspace_mismatch",
                    "Universe does not belong to workspace",
                )
            if universe.status != EquityUniverseStatus.ACTIVE.value:
                raise AppError(422, "equity_universe_inactive", "Universe is not active")
            members = await self.repository.list_members(
                universe_id=universe.id,
                is_active=True,
                limit=self.settings.equity_swing_scan_max_symbols,
                offset=0,
            )
            targets: list[EquitySwingScanTarget] = []
            for member in members:
                symbol = await self.validate_stock_symbol(member.symbol_id)
                if payload.filters.sector and member.sector != payload.filters.sector:
                    continue
                for timeframe in timeframes:
                    targets.append(
                        EquitySwingScanTarget(
                            symbol_id=member.symbol_id,
                            ticker=member.ticker or symbol.symbol,
                            timeframe=timeframe,
                            average_volume=member.average_volume,
                            source_id=payload.filters.source_id,
                            member_id=member.id,
                        )
                    )
            return targets
        if payload.watchlist_id is None:
            return []
        watchlist = await self.repository.get_watchlist(payload.watchlist_id)
        if watchlist is None:
            raise AppError(404, "market_watchlist_not_found", "Watchlist not found")
        if watchlist.workspace_id != payload.workspace_id:
            raise AppError(
                422,
                "watchlist_workspace_mismatch",
                "Watchlist does not belong to workspace",
            )
        if watchlist.status != MarketWatchlistStatus.ACTIVE.value:
            raise AppError(422, "watchlist_inactive", "Watchlist is not active")
        items = await self.repository.list_watchlist_items(
            watchlist_id=watchlist.id,
            limit=self.settings.equity_swing_scan_max_symbols,
        )
        targets = []
        requested_timeframes = [timeframe.value for timeframe in payload.timeframes]
        for item in items:
            symbol = await self.validate_stock_symbol(item.symbol_id)
            item_timeframes = requested_timeframes or [item.timeframe]
            for timeframe in item_timeframes:
                targets.append(
                    EquitySwingScanTarget(
                        symbol_id=item.symbol_id,
                        ticker=symbol.symbol,
                        timeframe=timeframe,
                        average_volume=None,
                        source_id=payload.filters.source_id or item.source_id,
                        watchlist_item_id=item.id,
                    )
                )
        return targets

    async def maybe_run_analysis(
        self,
        payload: EquitySwingScanCreate,
        target: EquitySwingScanTarget,
    ) -> UUID | None:
        if payload.options.use_existing_analysis_only:
            return None
        run = await self.analysis_service.create_live_window_run(
            LiveWindowAnalysisRunCreate(
                workspace_id=payload.workspace_id,
                symbol_id=target.symbol_id,
                source_id=target.source_id or payload.filters.source_id,
                timeframe=Timeframe(target.timeframe),
                lookback_minutes=self.settings.equity_swing_lookback_days * 1440,
                include_partial_live_candle=False,
                include_news_correlation=False,
                include_ai_explanation=False,
            )
        )
        if run.status != AnalysisRunStatus.COMPLETED.value:
            return run.id
        return run.id

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def validate_stock_symbol(self, symbol_id: UUID) -> Symbol:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Symbol is inactive")
        if symbol.market_type != MarketType.STOCK.value:
            raise AppError(
                422,
                "equity_symbol_required",
                "Equity research universes require stock symbols",
            )
        return symbol

    def member_from_payload(
        self,
        universe: EquityUniverse,
        symbol: Symbol,
        payload: EquityUniverseMemberCreate,
    ) -> EquityUniverseMember:
        return EquityUniverseMember(
            workspace_id=universe.workspace_id,
            universe_id=universe.id,
            symbol_id=symbol.id,
            ticker=payload.ticker or symbol.symbol,
            company_name=payload.company_name or symbol.display_name,
            sector=payload.sector,
            industry=payload.industry,
            exchange=payload.exchange,
            market_cap=payload.market_cap,
            average_volume=payload.average_volume,
            is_active=True,
            metadata_json=payload.metadata_json,
        )


def candidate_from_score(
    run: EquitySwingScanRun,
    target: EquitySwingScanTarget,
    score: EquitySwingScoreDraft,
    setup_context_id: UUID | None,
    signal_id: UUID | None,
    analysis_run_id: UUID | None,
) -> EquitySwingCandidate:
    return EquitySwingCandidate(
        workspace_id=run.workspace_id,
        scan_run_id=run.id,
        symbol_id=target.symbol_id,
        timeframe=target.timeframe,
        candidate_status=score.candidate_status.value,
        setup_type=score.setup_type.value,
        directional_bias=score.directional_bias.value,
        setup_quality_score=score.setup_quality_score,
        setup_quality_label=score.setup_quality_label.value,
        liquidity_score=score.liquidity_score,
        volume_score=score.volume_score,
        trend_quality_score=score.trend_quality_score,
        pullback_quality_score=score.pullback_quality_score,
        relative_strength_score=score.relative_strength_score,
        momentum_score=score.momentum_score,
        volatility_score=score.volatility_score,
        catalyst_score=score.catalyst_score,
        confidence_context_json=score.confidence_context_json,
        evidence_json=score.evidence_json,
        risk_notes_json=score.risk_notes_json,
        setup_context_id=setup_context_id,
        signal_id=signal_id,
        analysis_run_id=analysis_run_id,
        metadata_json={
            "ticker": target.ticker,
            "memberId": str(target.member_id) if target.member_id is not None else None,
            "watchlistItemId": (
                str(target.watchlist_item_id) if target.watchlist_item_id is not None else None
            ),
        },
    )


def setup_context_id_from_artifacts(artifacts: EquityResearchArtifacts) -> UUID | None:
    if artifacts.setup_context is None:
        return None
    return artifacts.setup_context.id


def analysis_run_id_from_artifacts(
    explicit_analysis_run_id: UUID | None,
    artifacts_analysis_run_id: UUID | None,
) -> UUID | None:
    return explicit_analysis_run_id or artifacts_analysis_run_id


def default_timeframes(value: str) -> list[str]:
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or ["1d", "4h", "1h"]


def candle_limit_for_timeframe(timeframe: str, lookback_days: int) -> int:
    per_day = {
        "1m": 390,
        "5m": 78,
        "15m": 26,
        "30m": 13,
        "1h": 8,
        "4h": 2,
        "1d": 1,
    }.get(timeframe, 1)
    return max(80, min(500, lookback_days * per_day))


def safe_error_message(error: Exception) -> str:
    message = str(error).strip()
    return message[:1000] if message else type(error).__name__
