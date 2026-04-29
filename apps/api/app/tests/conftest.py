import os
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.config import build_async_database_url, get_settings
from app.dependencies import database_session
from app.main import create_app
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.strategy_profiles.service import StrategyProfileService
from app.modules.symbols.models import MarketType, Symbol
from app.modules.users.models import User, UserRole
from app.modules.workspaces.models import Workspace


@pytest.fixture(scope="session")
def test_database_url() -> str:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url is None:
        pytest.skip("DB integration tests require TEST_DATABASE_URL")
    return test_url


@pytest.fixture(scope="session")
def migrated_test_database(test_database_url: str) -> Iterator[str]:
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()
    api_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(api_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(api_root / "alembic"))
    command.upgrade(alembic_config, "head")
    get_settings.cache_clear()
    try:
        yield test_database_url
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session")
async def integration_engine(migrated_test_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        build_async_database_url(SecretStr(migrated_test_database)),
        poolclass=NullPool,
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(integration_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with integration_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    test_app = create_app()

    async def override_database_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    test_app.dependency_overrides[database_session] = override_database_session
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def workspace(db_session: AsyncSession) -> Workspace:
    item = Workspace(name=f"Test Workspace {uuid4()}")
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def user(db_session: AsyncSession, workspace: Workspace) -> User:
    item = User(
        workspace_id=workspace.id,
        email=f"analyst-{uuid4()}@example.test",
        name="Integration Analyst",
        role=UserRole.ANALYST.value,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def eurusd_symbol(db_session: AsyncSession) -> Symbol:
    item = Symbol(
        symbol=f"EURUSD{uuid4().hex[:8]}",
        display_name="EUR/USD Integration",
        market_type=MarketType.FOREX.value,
        base_asset="EUR",
        quote_asset="USD",
        pip_size=Decimal("0.0001"),
        tick_size=Decimal("0.00001"),
        price_precision=5,
        quantity_precision=2,
        is_active=True,
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def json_data_source(db_session: AsyncSession, workspace: Workspace) -> DataSource:
    item = DataSource(
        workspace_id=workspace.id,
        name=f"JSON Fixture Source {uuid4()}",
        source_type=DataSourceType.JSON_IMPORT.value,
        provider="test_fixture",
        status=DataSourceStatus.ACTIVE.value,
        config_json={},
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def seeded_strategy_profiles(db_session: AsyncSession) -> None:
    service = StrategyProfileService(db_session)
    await service.seed_default_profiles()
    await db_session.flush()
