import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource
from app.modules.signals.service import SignalClassificationService
from app.modules.strategy_profiles.service import StrategyProfileService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import (
    assert_golden_expectation,
    load_golden_expectation,
    run_golden_analysis,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_analysis_run_with_persisted_candidates_produces_final_signal(
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

    assert_golden_expectation(result, load_golden_expectation("bullish_breakout_eurusd_1m"))


@pytest.mark.asyncio
async def test_fakeout_and_breakout_candidates_persist_protective_no_signal(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    result = await run_golden_analysis(
        db_session,
        "fakeout_protection_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )

    assert_golden_expectation(result, load_golden_expectation("fakeout_protection_eurusd_1m"))


@pytest.mark.asyncio
async def test_chop_candidate_stronger_than_directional_persists_no_signal(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    result = await run_golden_analysis(
        db_session,
        "range_chop_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )

    assert_golden_expectation(result, load_golden_expectation("range_chop_eurusd_1m"))


@pytest.mark.asyncio
async def test_strategy_profile_seed_is_idempotent(db_session: AsyncSession) -> None:
    service = StrategyProfileService(db_session)

    first_profiles = await service.seed_default_profiles()
    second_profiles = await service.seed_default_profiles()

    assert len(first_profiles) == 4
    assert {profile.id for profile in first_profiles} == {profile.id for profile in second_profiles}


@pytest.mark.asyncio
async def test_signal_artifacts_persist_with_components_evidence_and_risk_notes(
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
    seeded_strategy_profiles: None,
) -> None:
    result = await run_golden_analysis(
        db_session,
        "fakeout_protection_eurusd_1m",
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )

    assert result.signal_response is not None
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        result.analysis_run.id
    )
    assert signal_response.confidence_components
    assert signal_response.evidence
    assert signal_response.risk_notes


@pytest.mark.parametrize(
    "fixture_name",
    [
        "bullish_breakout_eurusd_1m",
        "fakeout_protection_eurusd_1m",
        "range_chop_eurusd_1m",
        "low_data_quality_missing_candles_eurusd_1m",
    ],
)
@pytest.mark.asyncio
async def test_golden_intelligence_fixture_matches_expectation(
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

    assert_golden_expectation(result, load_golden_expectation(fixture_name))
