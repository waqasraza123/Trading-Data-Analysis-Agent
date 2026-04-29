import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.data_sources.models import DataSource
from app.modules.engine_versions.models import EngineVersion
from app.modules.engine_versions.registry import (
    CURRENT_ENGINE_VERSIONS,
    current_engine_snapshot,
    is_supported_engine_snapshot,
)
from app.modules.engine_versions.service import EngineVersionService
from app.modules.seeding.service import SeedService
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.symbols.models import Symbol

pytestmark = pytest.mark.integration

EXPECTED_SYMBOLS = {"EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSDT", "ETHUSDT"}
EXPECTED_DATA_SOURCES = {"csv_upload", "json_import", "mock_live"}
EXPECTED_STRATEGY_PROFILES = {
    ("breakout_continuation", "v1"),
    ("reversal_rejection", "v1"),
    ("range_chop_avoidance", "v1"),
    ("fakeout_protection", "v1"),
}
EXPECTED_ENGINE_VERSIONS = {
    ("feature_engine", "v1"),
    ("indicator_engine", "v1"),
    ("pattern_engine", "v1"),
    ("signal_classifier", "v1"),
    ("deterministic_explanation_engine", "v1"),
    ("replay_engine", "v1"),
}


@pytest.mark.asyncio
async def test_seed_service_is_idempotent(db_session: AsyncSession) -> None:
    settings = Settings(
        _env_file=None,
        seed_default_workspace_name="Seed Workspace",
        seed_default_admin_email="Admin@Example.Test",
        seed_default_admin_name="Seed Admin",
    )
    service = SeedService(db_session)

    first_result = await service.seed(settings)
    second_result = await service.seed(settings)

    assert first_result.workspace_id == second_result.workspace_id
    assert first_result.admin_user_id == second_result.admin_user_id
    assert second_result.symbol_count == 6
    assert second_result.data_source_count == 3
    assert second_result.strategy_profile_count == 4
    assert second_result.engine_version_count == len(CURRENT_ENGINE_VERSIONS)


@pytest.mark.asyncio
async def test_seed_service_creates_required_defaults_without_duplicates(
    db_session: AsyncSession,
) -> None:
    settings = Settings(
        _env_file=None,
        seed_default_workspace_name="Seed Defaults Workspace",
        seed_default_admin_email="Admin@Example.Test",
        seed_default_admin_name="Seed Admin",
    )
    service = SeedService(db_session)

    await service.seed(settings)
    counts_after_first = await seeded_row_counts(db_session)
    await service.seed(settings)
    counts_after_second = await seeded_row_counts(db_session)

    symbol_result = await db_session.execute(select(Symbol.symbol))
    data_source_result = await db_session.execute(select(DataSource.name))
    profile_result = await db_session.execute(
        select(StrategyProfile.key, StrategyProfile.version)
    )
    engine_result = await db_session.execute(
        select(EngineVersion.engine_name, EngineVersion.version)
    )

    assert set(symbol_result.scalars().all()) == EXPECTED_SYMBOLS
    assert set(data_source_result.scalars().all()) == EXPECTED_DATA_SOURCES
    assert set(profile_result.all()) == EXPECTED_STRATEGY_PROFILES
    assert set(engine_result.all()) == EXPECTED_ENGINE_VERSIONS
    assert counts_after_second == counts_after_first


@pytest.mark.asyncio
async def test_engine_registry_snapshot_reports_current_versions() -> None:
    snapshot = current_engine_snapshot()

    assert is_supported_engine_snapshot(snapshot)
    engines = snapshot["engines"]
    assert isinstance(engines, dict)
    assert engines["feature_engine"]["version"] == "v1"
    assert engines["signal_classifier"]["version"] == "v1"
    assert engines["replay_engine"]["version"] == "v1"


@pytest.mark.asyncio
async def test_engine_version_service_seed_is_idempotent(db_session: AsyncSession) -> None:
    service = EngineVersionService(db_session)

    first_versions = await service.seed_current_versions()
    second_versions = await service.seed_current_versions()

    assert len(first_versions) == len(CURRENT_ENGINE_VERSIONS)
    assert {version.id for version in first_versions} == {version.id for version in second_versions}


@pytest.mark.asyncio
async def test_engine_versions_api_lists_seeded_versions(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await EngineVersionService(db_session).seed_current_versions()
    await db_session.commit()

    response = await api_client.get("/engine-versions")

    assert response.status_code == 200
    engine_names = {item["engineName"] for item in response.json()}
    assert {"feature_engine", "signal_classifier", "replay_engine"}.issubset(engine_names)


@pytest.mark.asyncio
async def test_engine_versions_api_filters_by_engine_name(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await EngineVersionService(db_session).seed_current_versions()
    await db_session.commit()

    response = await api_client.get("/engine-versions/feature_engine")

    assert response.status_code == 200
    assert response.json()[0]["engineName"] == "feature_engine"
    assert response.json()[0]["version"] == "v1"


@pytest.mark.asyncio
async def test_engine_versions_seed_api_is_idempotent(api_client: AsyncClient) -> None:
    first_response = await api_client.post("/engine-versions/seed")
    second_response = await api_client.post("/engine-versions/seed")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert set(second_response.json()["engineNames"]) == {
        engine_name for engine_name, _version in EXPECTED_ENGINE_VERSIONS
    }


@pytest.mark.asyncio
async def test_engine_versions_api_missing_engine_returns_clean_error(
    api_client: AsyncClient,
) -> None:
    response = await api_client.get("/engine-versions/missing_engine")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "engine_version_not_found"


async def seeded_row_counts(session: AsyncSession) -> dict[str, int]:
    symbols = await session.execute(select(func.count()).select_from(Symbol))
    data_sources = await session.execute(select(func.count()).select_from(DataSource))
    strategy_profiles = await session.execute(select(func.count()).select_from(StrategyProfile))
    engine_versions = await session.execute(select(func.count()).select_from(EngineVersion))
    return {
        "symbols": int(symbols.scalar_one()),
        "data_sources": int(data_sources.scalar_one()),
        "strategy_profiles": int(strategy_profiles.scalar_one()),
        "engine_versions": int(engine_versions.scalar_one()),
    }
