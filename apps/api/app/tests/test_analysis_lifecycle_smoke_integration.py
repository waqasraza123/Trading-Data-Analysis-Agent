import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRunStatus
from app.modules.analysis.schemas import LiveWindowAnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource
from app.modules.live.models import LiveFeedEventType
from app.modules.live.schemas import LiveProviderMessage, LiveSubscriptionCreate
from app.modules.live.service import LiveService
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import load_golden_candles, run_golden_analysis

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_historical_analysis_lifecycle_persists_all_smoke_artifacts(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    result = await run_golden_analysis(
        db_session,
        "bullish_breakout_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )
    service = AnalysisService(db_session)
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        result.analysis_run.id
    )
    audit_logs = await service.list_audit_logs(result.analysis_run.id)

    assert result.analysis_run.status == AnalysisRunStatus.COMPLETED
    assert await service.get_feature_snapshot(result.analysis_run.id) is not None
    assert await service.get_indicator_snapshot(result.analysis_run.id) is not None
    assert await service.list_pattern_candidates(result.analysis_run.id)
    assert signal_response.signal.classification_status == "signal"
    assert signal_response.confidence_components
    assert signal_response.evidence
    assert isinstance(signal_response.risk_notes, list)
    assert signal_response.deterministic_explanation is not None
    assert {audit_log.event_type for audit_log in audit_logs}.issuperset(
        {
            "analysis_created",
            "features_calculated",
            "indicators_calculated",
            "patterns_detected",
            "signals_calculated",
            "deterministic_explanations_calculated",
            "analysis_completed",
        }
    )


@pytest.mark.asyncio
async def test_live_window_analysis_lifecycle_uses_mock_live_final_candles(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    live_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    candles = load_golden_candles("bullish_breakout_eurusd_1m")
    live_service = LiveService(db_session)
    subscription = await live_service.create_subscription(
        LiveSubscriptionCreate(
            workspace_id=workspace.id,
            source_id=live_data_source.id,
            symbol_id=eurusd_symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            provider="mock",
        )
    )
    for candle in candles:
        await live_service.ingest_provider_message(
            subscription.id,
            LiveProviderMessage(
                event_type=LiveFeedEventType.CANDLE_FINAL,
                provider_timestamp=candle.timestamp,
                payload_json={"candle": candle.model_dump(mode="json")},
            ),
        )

    analysis_run = await AnalysisService(db_session).create_live_window_run(
        LiveWindowAnalysisRunCreate(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=live_data_source.id,
            symbol_id=eurusd_symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            lookback_minutes=11,
            warmup_candles=12,
            baseline_candles=12,
        )
    )
    service = AnalysisService(db_session)
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        analysis_run.id
    )

    assert analysis_run.status == AnalysisRunStatus.COMPLETED
    assert await service.get_feature_snapshot(analysis_run.id) is not None
    assert await service.get_indicator_snapshot(analysis_run.id) is not None
    assert await service.list_pattern_candidates(analysis_run.id)
    assert signal_response.signal.analysis_run_id == analysis_run.id
    assert signal_response.deterministic_explanation is not None
