from datetime import UTC, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource
from app.modules.imports.models import ImportBatchStatus
from app.modules.live.models import LiveFeedEventProcessingStatus
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.conftest import (
    candle_payloads_to_csv,
    deterministic_candle_payloads,
    import_deterministic_json_candles,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_json_historical_ingestion_stores_queryable_final_candles(
    api_client: AsyncClient,
    db_session: AsyncSession,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    json_data_source: DataSource,
) -> None:
    batch, candles = await import_deterministic_json_candles(
        db_session,
        workspace,
        user,
        eurusd_symbol,
        json_data_source,
    )

    assert batch.status == ImportBatchStatus.COMPLETED
    assert batch.rows_received == len(candles)
    assert batch.rows_valid == len(candles)

    list_response = await api_client.get(
        "/candles",
        params={
            "workspace_id": str(workspace.id),
            "symbol_id": str(eurusd_symbol.id),
            "source_id": str(json_data_source.id),
            "timeframe": "1m",
            "start_time": candles[0].timestamp.isoformat(),
            "end_time": candles[-1].timestamp.isoformat(),
        },
    )
    count_response = await api_client.get(
        "/candles/count",
        params={
            "workspace_id": str(workspace.id),
            "symbol_id": str(eurusd_symbol.id),
            "source_id": str(json_data_source.id),
            "timeframe": "1m",
            "start_time": candles[0].timestamp.isoformat(),
            "end_time": candles[-1].timestamp.isoformat(),
        },
    )
    quality_response = await api_client.get(
        "/candles/quality",
        params={
            "workspace_id": str(workspace.id),
            "symbol_id": str(eurusd_symbol.id),
            "source_id": str(json_data_source.id),
            "timeframe": "1m",
            "start_time": candles[0].timestamp.isoformat(),
            "end_time": candles[-1].timestamp.isoformat(),
        },
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == len(candles)
    assert count_response.status_code == 200
    assert count_response.json()["count"] == len(candles)
    assert quality_response.status_code == 200
    assert quality_response.json()["expectedCandles"] == len(candles)
    assert quality_response.json()["missingCandles"] == 0


@pytest.mark.asyncio
async def test_csv_historical_ingestion_stores_queryable_final_candles(
    api_client: AsyncClient,
    workspace: Workspace,
    user: User,
    eurusd_symbol: Symbol,
    csv_data_source: DataSource,
) -> None:
    candles = deterministic_candle_payloads()
    response = await api_client.post(
        "/imports/candles/csv",
        data={
            "workspace_id": str(workspace.id),
            "user_id": str(user.id),
            "source_id": str(csv_data_source.id),
            "symbol_id": str(eurusd_symbol.id),
            "timeframe": "1m",
        },
        files={
            "file": (
                "candles.csv",
                candle_payloads_to_csv(candles).encode(),
                "text/csv",
            )
        },
    )

    assert response.status_code == 201
    batch = response.json()
    assert batch["status"] == "completed"
    assert batch["rowsValid"] == len(candles)

    latest_response = await api_client.get(
        "/candles/latest",
        params={
            "workspace_id": str(workspace.id),
            "symbol_id": str(eurusd_symbol.id),
            "source_id": str(csv_data_source.id),
            "timeframe": "1m",
        },
    )

    assert latest_response.status_code == 200
    assert latest_response.json()["timestamp"] == candles[-1].timestamp.isoformat().replace(
        "+00:00",
        "Z",
    )


@pytest.mark.asyncio
async def test_mock_live_partial_final_and_ignored_subscription_events(
    api_client: AsyncClient,
    db_session: AsyncSession,
    workspace: Workspace,
    eurusd_symbol: Symbol,
    live_data_source: DataSource,
) -> None:
    create_response = await api_client.post(
        "/live/subscriptions",
        json={
            "workspaceId": str(workspace.id),
            "sourceId": str(live_data_source.id),
            "symbolId": str(eurusd_symbol.id),
            "timeframe": "1m",
            "provider": "mock",
        },
    )
    assert create_response.status_code == 201
    subscription_id = create_response.json()["id"]
    timestamp = datetime(2026, 1, 3, 12, 0, tzinfo=UTC)

    partial_response = await api_client.post(
        f"/live/subscriptions/{subscription_id}/events",
        json=live_candle_message("candle_partial", timestamp, "1.1006"),
    )
    final_response = await api_client.post(
        f"/live/subscriptions/{subscription_id}/events",
        json=live_candle_message("candle_final", timestamp, "1.1010"),
    )
    latest_final = await CandleService(db_session).get_latest_candle(
        workspace_id=workspace.id,
        symbol_id=eurusd_symbol.id,
        timeframe=Timeframe.ONE_MINUTE,
        source_id=live_data_source.id,
        is_final=True,
    )

    assert partial_response.status_code == 202
    assert partial_response.json()["processingStatus"] == LiveFeedEventProcessingStatus.PROCESSED
    assert final_response.status_code == 202
    assert final_response.json()["processingStatus"] == LiveFeedEventProcessingStatus.PROCESSED
    assert latest_final.is_final is True
    assert latest_final.close == Decimal("1.1010")

    pause_response = await api_client.post(f"/live/subscriptions/{subscription_id}/pause")
    ignored_response = await api_client.post(
        f"/live/subscriptions/{subscription_id}/events",
        json=live_candle_message("candle_partial", timestamp, "1.1012"),
    )

    assert pause_response.status_code == 200
    assert ignored_response.status_code == 202
    assert ignored_response.json()["processingStatus"] == LiveFeedEventProcessingStatus.IGNORED

    stop_response = await api_client.post(f"/live/subscriptions/{subscription_id}/stop")
    stopped_ignored_response = await api_client.post(
        f"/live/subscriptions/{subscription_id}/events",
        json=live_candle_message("candle_partial", timestamp, "1.1014"),
    )

    assert stop_response.status_code == 200
    assert stopped_ignored_response.status_code == 202
    assert (
        stopped_ignored_response.json()["processingStatus"] == LiveFeedEventProcessingStatus.IGNORED
    )


def live_candle_message(event_type: str, timestamp: datetime, close: str) -> dict[str, object]:
    return {
        "eventType": event_type,
        "providerTimestamp": timestamp.isoformat(),
        "payloadJson": {
            "candle": {
                "timestamp": timestamp.isoformat(),
                "open": "1.1000",
                "high": "1.1020",
                "low": "1.0995",
                "close": close,
                "volume": "120",
            }
        },
    }
