from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.modules.analysis.models import AnalysisReplayMode
from app.modules.analysis.schemas import AnalysisReplayRequest, AnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource
from app.modules.imports.schemas import JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.llm_explanations.service import LlmExplanationService
from app.modules.news.models import NewsEvent, NewsEventType, NewsImportance, NewsSentiment
from app.modules.news.repository import NewsCorrelationRepository
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import load_golden_candles

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analysis_with_news_and_llm_runs_news_before_llm(
    monkeypatch: pytest.MonkeyPatch,
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    monkeypatch.setenv("LLM_EXPLANATIONS_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_STORE_INPUTS", "true")
    get_settings.cache_clear()
    candles = load_golden_candles("bullish_breakout_eurusd_1m")
    await ImportService(db_session).process_json_import(
        JsonCandleImportRequest(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=json_data_source.id,
            symbol_id=eurusd_symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            candles=candles,
        )
    )
    db_session.add(
        NewsEvent(
            workspace_id=workspace.id,
            source="manual",
            event_type=NewsEventType.ECONOMIC_CALENDAR.value,
            title="USD CPI Release",
            event_time=candles[12].timestamp - timedelta(minutes=4),
            currency="USD",
            asset=None,
            symbol_id=None,
            importance=NewsImportance.HIGH.value,
            sentiment=NewsSentiment.BULLISH.value,
            raw_payload_json={},
        )
    )
    await db_session.flush()

    run = await AnalysisService(db_session).create_historical_run(
        AnalysisRunCreate(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=json_data_source.id,
            symbol_id=eurusd_symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            start_time=candles[12].timestamp,
            end_time=candles[-1].timestamp,
            warmup_start_time=candles[0].timestamp,
            baseline_start_time=candles[0].timestamp,
            include_news_correlation=True,
            include_ai_explanation=True,
        )
    )
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(run.id)
    audit_logs = await AnalysisService(db_session).list_audit_logs(run.id)
    event_types = [log.event_type for log in audit_logs]

    assert signal_response.news_correlations
    assert signal_response.llm_explanation is not None
    assert signal_response.llm_explanation.input_json is not None
    assert signal_response.llm_explanation.input_json["news_correlations"]
    assert event_types.index("news_correlation_started") < event_types.index(
        "llm_explanation_requested"
    )
    await LlmExplanationService(db_session).generate_for_signal(signal_response.signal.id)
    await LlmExplanationService(db_session).generate_for_signal(signal_response.signal.id)
    llm_count = await db_session.scalar(
        select(func.count())
        .select_from(LlmExplanation)
        .where(LlmExplanation.signal_id == signal_response.signal.id)
    )
    assert llm_count == 1

    replay = await AnalysisService(db_session).replay_run(
        run.id,
        AnalysisReplayRequest(mode=AnalysisReplayMode.LATEST_ENGINE_VERSION),
    )
    original_correlations = await NewsCorrelationRepository(db_session).list_by_analysis_run_id(
        run.id
    )
    replay_correlations = await NewsCorrelationRepository(db_session).list_by_analysis_run_id(
        replay.id
    )

    assert replay.replayed_from_analysis_run_id == run.id
    assert original_correlations
    assert replay_correlations
    assert all(correlation.analysis_run_id == run.id for correlation in original_correlations)
    get_settings.cache_clear()
