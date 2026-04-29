from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.analysis.models import (
    AnalysisMode,
    AnalysisReplayMode,
    AnalysisRun,
    AnalysisRunStatus,
)
from app.modules.analysis.schemas import AnalysisReplayRequest
from app.modules.analysis.service import AnalysisService
from app.modules.data_sources.models import DataSource
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import run_golden_analysis

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_replay_creates_new_linked_analysis_run_without_mutating_original(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    original = await run_golden_analysis(
        db_session,
        "bullish_breakout_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )
    assert original.signal_response is not None
    original_signal_id = original.signal_response.signal.id
    assert original.signal_response.deterministic_explanation is not None
    original_explanation_id = original.signal_response.deterministic_explanation.id

    replay_run = await AnalysisService(db_session).replay_run(
        original.analysis_run.id,
        AnalysisReplayRequest(mode=AnalysisReplayMode.LATEST_ENGINE_VERSION),
    )
    replay_signal = await SignalClassificationService(db_session).get_by_analysis_run_id(
        replay_run.id
    )
    original_signal = await SignalClassificationService(db_session).get_by_analysis_run_id(
        original.analysis_run.id
    )

    assert replay_run.id != original.analysis_run.id
    assert replay_run.analysis_mode == AnalysisMode.REPLAY
    assert replay_run.replayed_from_analysis_run_id == original.analysis_run.id
    assert replay_run.replay_mode == AnalysisReplayMode.LATEST_ENGINE_VERSION
    assert replay_run.status == AnalysisRunStatus.COMPLETED
    assert replay_run.engine_snapshot_json is not None
    assert replay_run.rule_set_snapshot_json is not None
    assert replay_signal.signal.classification_status == "signal"
    assert replay_signal.deterministic_explanation is not None
    assert replay_signal.deterministic_explanation.signal_id == replay_signal.signal.id
    assert replay_signal.deterministic_explanation.analysis_run_id == replay_run.id
    assert replay_signal.signal.id != original_signal_id
    assert original_signal.signal.id == original_signal_id
    assert original_signal.deterministic_explanation is not None
    assert original_signal.deterministic_explanation.id == original_explanation_id
    assert original.analysis_run.analysis_mode == AnalysisMode.HISTORICAL
    assert original.analysis_run.replayed_from_analysis_run_id is None


@pytest.mark.asyncio
async def test_replay_api_smoke_exercises_latest_and_same_engine_modes(
    api_client: AsyncClient,
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    original = await run_golden_analysis(
        db_session,
        "bullish_breakout_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )
    assert original.signal_response is not None
    assert original.signal_response.deterministic_explanation is not None
    original_signal_id = original.signal_response.signal.id
    original_explanation_id = original.signal_response.deterministic_explanation.id

    latest_response = await api_client.post(
        f"/analysis-runs/{original.analysis_run.id}/replay",
        json={"mode": "latest_engine_version"},
    )
    same_response = await api_client.post(
        f"/analysis-runs/{original.analysis_run.id}/replay",
        json={"mode": "same_engine_version"},
    )
    original_signal = await SignalClassificationService(db_session).get_by_analysis_run_id(
        original.analysis_run.id
    )

    assert latest_response.status_code == 200
    assert latest_response.json()["originalAnalysisRunId"] == str(original.analysis_run.id)
    assert latest_response.json()["status"] == "completed"
    assert same_response.status_code == 200
    assert same_response.json()["originalAnalysisRunId"] == str(original.analysis_run.id)
    assert same_response.json()["status"] == "completed"
    assert latest_response.json()["replayAnalysisRunId"] != str(original.analysis_run.id)
    assert same_response.json()["replayAnalysisRunId"] != str(original.analysis_run.id)
    assert latest_response.json()["replayAnalysisRunId"] != same_response.json()[
        "replayAnalysisRunId"
    ]
    assert original_signal.signal.id == original_signal_id
    assert original_signal.deterministic_explanation is not None
    assert original_signal.deterministic_explanation.id == original_explanation_id


@pytest.mark.asyncio
async def test_replay_invalid_analysis_run_id_returns_clean_error(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        f"/analysis-runs/{uuid4()}/replay",
        json={"mode": "latest_engine_version"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "analysis_run_not_found"


@pytest.mark.asyncio
async def test_same_engine_replay_uses_original_version_snapshot_when_supported(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    original = await run_golden_analysis(
        db_session,
        "bullish_breakout_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )
    assert original.analysis_run.engine_snapshot_json is not None
    assert original.analysis_run.rule_set_snapshot_json is not None

    replay_run = await AnalysisService(db_session).replay_run(
        original.analysis_run.id,
        AnalysisReplayRequest(mode=AnalysisReplayMode.SAME_ENGINE_VERSION),
    )
    replay_signal = await SignalClassificationService(db_session).get_by_analysis_run_id(
        replay_run.id
    )

    assert replay_run.status == AnalysisRunStatus.COMPLETED
    assert replay_run.replay_mode == AnalysisReplayMode.SAME_ENGINE_VERSION
    assert replay_run.engine_version == original.analysis_run.engine_version
    assert replay_run.rule_set_version == original.analysis_run.rule_set_version
    assert replay_run.engine_snapshot_json == original.analysis_run.engine_snapshot_json
    assert replay_run.rule_set_snapshot_json is not None
    assert "strategyProfileSnapshot" in replay_run.rule_set_snapshot_json
    assert replay_signal.signal.strategy_profile_key == "breakout_continuation"
    assert replay_signal.signal.strategy_profile_version == "v1"


@pytest.mark.asyncio
async def test_same_engine_replay_returns_explicit_unsupported_error(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    original = await run_golden_analysis(
        db_session,
        "bullish_breakout_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )
    original.analysis_run.engine_snapshot_json = {
        "engines": {
            "signal_classifier": {
                "version": "v999",
                "description": "unsupported",
                "config": {},
            }
        }
    }
    await db_session.flush()

    with pytest.raises(AppError) as error_info:
        await AnalysisService(db_session).replay_run(
            original.analysis_run.id,
            AnalysisReplayRequest(mode=AnalysisReplayMode.SAME_ENGINE_VERSION),
        )

    assert error_info.value.status_code == 422
    assert error_info.value.code == "unsupported_engine_version"

    audit_logs = await AnalysisService(db_session).list_audit_logs(original.analysis_run.id)
    event_types = [audit_log.event_type for audit_log in audit_logs]
    assert "analysis_replay_requested" in event_types
    assert "analysis_replay_unsupported_engine_version" in event_types


@pytest.mark.asyncio
async def test_replay_incomplete_original_run_returns_clean_error(
    api_client: AsyncClient,
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
) -> None:
    incomplete_run = await AnalysisService(db_session).repository.create_run(
        build_completed_run_without_source(workspace, user, eurusd_symbol)
    )
    await db_session.flush()

    response = await api_client.post(
        f"/analysis-runs/{incomplete_run.id}/replay",
        json={"mode": "latest_engine_version"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "analysis_run_missing_source_context"


def build_completed_run_without_source(
    workspace: Workspace,
    user: User,
    symbol: Symbol,
) -> AnalysisRun:
    from datetime import UTC, datetime

    from app.modules.analysis.service import (
        ANALYSIS_LIFECYCLE_ENGINE_VERSION,
        ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
    )

    return AnalysisRun(
        workspace_id=workspace.id,
        user_id=user.id,
        symbol_id=symbol.id,
        source_id=None,
        timeframe="1m",
        start_time=datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
        warmup_start_time=None,
        baseline_start_time=None,
        analysis_mode=AnalysisMode.HISTORICAL,
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        status=AnalysisRunStatus.COMPLETED,
        engine_version=ANALYSIS_LIFECYCLE_ENGINE_VERSION,
        rule_set_version=ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
        engine_snapshot_json=None,
        rule_set_snapshot_json=None,
    )
