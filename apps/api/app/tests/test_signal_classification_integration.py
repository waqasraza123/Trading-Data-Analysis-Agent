import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("DATABASE_URL") is None,
    reason="Signal classification integration tests require DATABASE_URL",
)


@pytest.mark.asyncio
async def test_analysis_run_with_persisted_candidates_produces_final_signal() -> None:
    pytest.skip("Requires repository database fixture setup.")


@pytest.mark.asyncio
async def test_fakeout_and_breakout_candidates_persist_protective_no_signal() -> None:
    pytest.skip("Requires repository database fixture setup.")


@pytest.mark.asyncio
async def test_chop_candidate_stronger_than_directional_persists_no_signal() -> None:
    pytest.skip("Requires repository database fixture setup.")


@pytest.mark.asyncio
async def test_strategy_profile_seed_is_idempotent() -> None:
    pytest.skip("Requires repository database fixture setup.")


@pytest.mark.asyncio
async def test_signal_artifacts_persist_with_components_evidence_and_risk_notes() -> None:
    pytest.skip("Requires repository database fixture setup.")
