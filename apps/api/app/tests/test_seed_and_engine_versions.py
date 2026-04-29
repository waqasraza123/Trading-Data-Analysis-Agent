import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.engine_versions.registry import (
    CURRENT_ENGINE_VERSIONS,
    current_engine_snapshot,
    is_supported_engine_snapshot,
)
from app.modules.engine_versions.service import EngineVersionService
from app.modules.seeding.service import SeedService

pytestmark = pytest.mark.integration


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
