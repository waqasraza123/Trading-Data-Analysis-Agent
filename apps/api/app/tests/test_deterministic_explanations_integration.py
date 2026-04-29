import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource
from app.modules.explanations.service import DeterministicExplanationService
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import run_golden_analysis

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_normal_analysis_produces_signal_and_deterministic_explanation(
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

    assert result.signal_response is not None
    explanation = result.signal_response.deterministic_explanation
    assert explanation is not None
    assert explanation.signal_id == result.signal_response.signal.id
    assert explanation.analysis_run_id == result.analysis_run.id
    assert explanation.safety_status == "passed"
    assert explanation.short_summary
    assert explanation.full_text


@pytest.mark.asyncio
async def test_manual_classify_recomputes_signal_and_deterministic_explanation_safely(
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
    assert result.signal_response is not None
    original_signal_id = result.signal_response.signal.id
    assert result.signal_response.deterministic_explanation is not None
    original_explanation_id = result.signal_response.deterministic_explanation.id

    recomputed = await SignalClassificationService(db_session).classify_analysis_run(
        result.analysis_run.id
    )

    assert recomputed.signal.id != original_signal_id
    assert recomputed.deterministic_explanation is not None
    assert recomputed.deterministic_explanation.id != original_explanation_id
    assert recomputed.deterministic_explanation.signal_id == recomputed.signal.id
    assert recomputed.signal.classification_status == "signal"


@pytest.mark.asyncio
async def test_repeated_deterministic_explanation_generation_is_idempotent(
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
    assert result.signal_response is not None
    signal_id = result.signal_response.signal.id
    service = DeterministicExplanationService(db_session)

    first = await service.generate_for_signal_id(signal_id)
    second = await service.generate_for_signal_id(signal_id)

    assert first.id == second.id
    assert first.signal_id == signal_id
    assert second.signal_id == signal_id
    assert first.full_text == second.full_text


@pytest.mark.asyncio
async def test_signal_retrieval_includes_deterministic_explanation(
    api_client: AsyncClient,
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
    assert result.signal_response is not None

    response = await api_client.get(f"/signals/{result.signal_response.signal.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["id"] == str(result.signal_response.signal.id)
    assert payload["deterministicExplanation"]["signalId"] == str(result.signal_response.signal.id)
    assert payload["deterministicExplanation"]["safetyStatus"] == "passed"


@pytest.mark.parametrize(
    "fixture_name",
    ["fakeout_protection_eurusd_1m", "range_chop_eurusd_1m"],
)
@pytest.mark.asyncio
async def test_no_signal_cases_produce_safe_deterministic_explanations(
    fixture_name: str,
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    result = await run_golden_analysis(
        db_session,
        fixture_name,
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )

    assert result.signal_response is not None
    assert result.signal_response.signal.classification_status == "no_signal"
    explanation = result.signal_response.deterministic_explanation
    assert explanation is not None
    assert explanation.safety_status == "passed"
    assert explanation.no_signal_summary is not None
    assert "No signal" in explanation.no_signal_summary
