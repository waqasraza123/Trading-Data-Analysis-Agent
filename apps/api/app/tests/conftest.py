import os
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from alembic import command
from app.config import AppEnvironment, Settings, build_async_database_url, get_settings
from app.core.database_safety import UnsafeDatabaseTargetError, validate_test_database_target
from app.dependencies import database_session
from app.main import create_app
from app.modules.analysis.models import AnalysisRun
from app.modules.analysis.schemas import AnalysisRunCreate, LiveWindowAnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.imports.models import ImportBatch
from app.modules.imports.schemas import CsvCandleImportRequest, JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.seeding.service import SeedResult, SeedService
from app.modules.strategy_profiles.service import StrategyProfileService
from app.modules.symbols.models import MarketType, Symbol
from app.modules.users.models import User, UserRole
from app.modules.workspaces.models import Workspace

TEST_DATABASE_SKIP_REASON = "DB integration tests require TEST_DATABASE_URL"
APP_TABLES = (
    "scenario_hypotheses",
    "llm_reasoning_runs",
    "llm_explanations",
    "deterministic_explanations",
    "signal_news_correlations",
    "signal_risk_notes",
    "signal_evidence",
    "signal_confidence_components",
    "signals",
    "news_events",
    "chart_screenshot_runs",
    "pattern_candidates",
    "indicator_snapshots",
    "feature_snapshots",
    "analysis_audit_logs",
    "analysis_runs",
    "live_feed_events",
    "live_feed_subscriptions",
    "candles",
    "import_errors",
    "import_batches",
    "strategy_profiles",
    "engine_versions",
    "data_sources",
    "users",
    "workspaces",
    "symbols",
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("TEST_DATABASE_URL"):
        validate_test_database_url_safety()
        return
    skip_marker = pytest.mark.skip(reason=TEST_DATABASE_SKIP_REASON)
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_marker)


def validate_test_database_url_safety() -> None:
    test_url = os.environ.get("TEST_DATABASE_URL")
    database_url = os.environ.get("DATABASE_URL")
    try:
        validate_test_database_target(
            test_database_url=test_url,
            database_url=database_url,
            app_env=os.environ.get("APP_ENV"),
            env=os.environ.get("ENV"),
            operation_name="DB integration tests",
        )
    except UnsafeDatabaseTargetError as error:
        pytest.fail(
            str(error),
            pytrace=False,
        )


@pytest.fixture(scope="session")
def test_database_url() -> str:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url is None:
        pytest.skip(TEST_DATABASE_SKIP_REASON)
    validate_test_database_url_safety()
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
        await clear_integration_database(engine)
        yield engine
    finally:
        await clear_integration_database(engine)
        await engine.dispose()


async def clear_integration_database(engine: AsyncEngine) -> None:
    table_names = ", ".join(APP_TABLES)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


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
    settings = integration_api_settings()
    test_app = create_app(settings)

    async def override_database_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    test_app.dependency_overrides[database_session] = override_database_session
    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
        headers=api_auth_headers(settings),
    ) as client:
        yield client
    test_app.dependency_overrides.clear()


def integration_api_settings() -> Settings:
    return get_settings().model_copy(
        update={
            "app_env": AppEnvironment.TEST,
            "rate_limit_enabled": False,
        }
    )


def api_auth_headers(settings: Settings) -> dict[str, str]:
    if not settings.auth_enabled or settings.admin_api_key is None:
        return {}
    return {settings.api_key_header_name: settings.admin_api_key.get_secret_value()}


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


@pytest_asyncio.fixture
async def csv_data_source(db_session: AsyncSession, workspace: Workspace) -> DataSource:
    item = DataSource(
        workspace_id=workspace.id,
        name=f"CSV Fixture Source {uuid4()}",
        source_type=DataSourceType.CSV_UPLOAD.value,
        provider="test_csv",
        status=DataSourceStatus.ACTIVE.value,
        config_json={},
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def live_data_source(db_session: AsyncSession, workspace: Workspace) -> DataSource:
    item = DataSource(
        workspace_id=workspace.id,
        name=f"Mock Live Fixture Source {uuid4()}",
        source_type=DataSourceType.WEBSOCKET_LIVE.value,
        provider="mock",
        status=DataSourceStatus.ACTIVE.value,
        config_json={},
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture
async def seeded_defaults(db_session: AsyncSession) -> SeedResult:
    result = await SeedService(db_session).seed(
        get_settings().model_copy(
            update={
                "seed_default_workspace_name": f"Seed Workspace {uuid4()}",
                "seed_default_admin_email": f"admin-{uuid4()}@example.test",
                "seed_default_admin_name": "Seed Admin",
            }
        )
    )
    await db_session.flush()
    return result


def deterministic_candle_payloads(
    count: int = 24,
    start_time: datetime | None = None,
) -> list[RawCandlePayload]:
    resolved_start = start_time or datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    candles: list[RawCandlePayload] = []
    for index in range(count):
        base = Decimal("1.1000") + (Decimal(index) * Decimal("0.0005"))
        candles.append(
            RawCandlePayload(
                timestamp=resolved_start + timedelta(minutes=index),
                open=str(base),
                high=str(base + Decimal("0.0008")),
                low=str(base - Decimal("0.0002")),
                close=str(base + Decimal("0.0006")),
                volume=str(Decimal("100") + Decimal(index)),
            )
        )
    return candles


def candle_payloads_to_csv(candles: list[RawCandlePayload]) -> str:
    rows = ["timestamp,open,high,low,close,volume"]
    for candle in candles:
        rows.append(
            ",".join(
                [
                    candle.timestamp.isoformat().replace("+00:00", "Z"),
                    str(candle.open),
                    str(candle.high),
                    str(candle.low),
                    str(candle.close),
                    str(candle.volume),
                ]
            )
        )
    return "\n".join(rows)


async def import_deterministic_json_candles(
    session: AsyncSession,
    workspace: Workspace,
    user: User,
    symbol: Symbol,
    data_source: DataSource,
    candles: list[RawCandlePayload] | None = None,
) -> tuple[ImportBatch, list[RawCandlePayload]]:
    resolved_candles = candles or deterministic_candle_payloads()
    batch = await ImportService(session).process_json_import(
        JsonCandleImportRequest(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=data_source.id,
            symbol_id=symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            candles=resolved_candles,
        )
    )
    return batch, resolved_candles


async def import_deterministic_csv_candles(
    session: AsyncSession,
    workspace: Workspace,
    user: User,
    symbol: Symbol,
    data_source: DataSource,
    candles: list[RawCandlePayload] | None = None,
) -> tuple[ImportBatch, list[RawCandlePayload]]:
    resolved_candles = candles or deterministic_candle_payloads()
    batch = await ImportService(session).process_csv_import(
        payload=CsvCandleImportRequest(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=data_source.id,
            symbol_id=symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            file_name="deterministic-smoke.csv",
        ),
        csv_text=candle_payloads_to_csv(resolved_candles),
    )
    return batch, resolved_candles


async def create_completed_historical_analysis(
    session: AsyncSession,
    workspace: Workspace,
    user: User,
    symbol: Symbol,
    data_source: DataSource,
) -> tuple[AnalysisRun, ImportBatch, list[RawCandlePayload]]:
    batch, candles = await import_deterministic_json_candles(
        session,
        workspace,
        user,
        symbol,
        data_source,
    )
    run = await AnalysisService(session).create_historical_run(
        AnalysisRunCreate(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=data_source.id,
            symbol_id=symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            start_time=candles[12].timestamp,
            end_time=candles[-1].timestamp,
            warmup_start_time=candles[0].timestamp,
            baseline_start_time=candles[0].timestamp,
        )
    )
    return run, batch, candles


async def create_completed_live_window_analysis(
    session: AsyncSession,
    workspace: Workspace,
    user: User,
    symbol: Symbol,
    data_source: DataSource,
) -> tuple[AnalysisRun, ImportBatch, list[RawCandlePayload]]:
    batch, candles = await import_deterministic_json_candles(
        session,
        workspace,
        user,
        symbol,
        data_source,
        candles=deterministic_candle_payloads(
            count=24,
            start_time=datetime(2026, 1, 2, 0, 0, tzinfo=UTC),
        ),
    )
    run = await AnalysisService(session).create_live_window_run(
        LiveWindowAnalysisRunCreate(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=data_source.id,
            symbol_id=symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            lookback_minutes=11,
            warmup_candles=12,
            baseline_candles=12,
        )
    )
    return run, batch, candles
