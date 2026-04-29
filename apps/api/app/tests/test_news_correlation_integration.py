from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tests.golden.helpers import run_golden_analysis

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_news_event_api_create_import_query_and_update(
    api_client: AsyncClient,
    workspace: Workspace,
) -> None:
    create_response = await api_client.post(
        "/news-events",
        json={
            "workspaceId": str(workspace.id),
            "source": "manual",
            "eventType": "economic_calendar",
            "title": "USD CPI Release",
            "eventTime": "2026-04-29T12:30:00Z",
            "currency": "usd",
            "importance": "high",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["currency"] == "USD"
    assert created["rawPayloadJson"]["currency"] == "usd"

    import_response = await api_client.post(
        "/news-events/import-json",
        json=[
            {
                "workspaceId": str(workspace.id),
                "source": "manual",
                "eventType": "market_news",
                "title": "EUR Market Headline",
                "eventTime": "2026-04-29T12:35:00Z",
                "asset": "eur",
            }
        ],
    )
    list_response = await api_client.get(
        "/news-events",
        params={"workspaceId": str(workspace.id), "currency": "USD"},
    )
    patch_response = await api_client.patch(
        f"/news-events/{created['id']}",
        json={"sentiment": "mixed"},
    )

    assert import_response.status_code == 201
    assert import_response.json()["importedCount"] == 1
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == created["id"]
    assert patch_response.status_code == 200
    assert patch_response.json()["sentiment"] == "mixed"


@pytest.mark.asyncio
async def test_manual_signal_news_correlation_persists_and_is_idempotent(
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
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        result.analysis_run.id
    )
    event_time = result.analysis_run.start_time - timedelta(minutes=4)
    create_event = await api_client.post(
        "/news-events",
        json={
            "workspaceId": str(workspace.id),
            "source": "manual",
            "eventType": "economic_calendar",
            "title": "USD CPI Release",
            "eventTime": event_time.isoformat(),
            "currency": "USD",
            "importance": "high",
            "sentiment": "bullish",
        },
    )

    first_response = await api_client.post(
        f"/signals/{signal_response.signal.id}/correlate-news"
    )
    second_response = await api_client.post(
        f"/signals/{signal_response.signal.id}/correlate-news"
    )
    list_response = await api_client.get(
        f"/analysis-runs/{result.analysis_run.id}/news-correlations"
    )

    assert create_event.status_code == 201
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["correlationCount"] == 1
    assert second_response.json()["correlationCount"] == 1
    assert list_response.status_code == 200
    correlations = list_response.json()
    assert len(correlations) == 1
    assert correlations[0]["correlationLabel"] in {"possible", "strong"}
    assert correlations[0]["newsEventId"] == create_event.json()["id"]
    assert "possible correlation" in correlations[0]["reason"].lower()


@pytest.mark.asyncio
async def test_event_outside_window_does_not_create_strong_correlation(
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
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        result.analysis_run.id
    )
    await api_client.post(
        "/news-events",
        json={
            "workspaceId": str(workspace.id),
            "source": "manual",
            "eventType": "economic_calendar",
            "title": "Old USD Event",
            "eventTime": (result.analysis_run.start_time - timedelta(hours=2)).isoformat(),
            "currency": "USD",
            "importance": "critical",
        },
    )

    response = await api_client.post(f"/signals/{signal_response.signal.id}/correlate-news")

    assert response.status_code == 200
    assert response.json()["correlationCount"] == 0


@pytest.mark.asyncio
async def test_unrelated_currency_event_does_not_correlate_strongly(
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
    signal_response = await SignalClassificationService(db_session).get_by_analysis_run_id(
        result.analysis_run.id
    )
    await api_client.post(
        "/news-events",
        json={
            "workspaceId": str(workspace.id),
            "source": "manual",
            "eventType": "economic_calendar",
            "title": "JPY Event",
            "eventTime": (result.analysis_run.start_time - timedelta(minutes=1)).isoformat(),
            "currency": "JPY",
            "importance": "critical",
        },
    )

    response = await api_client.post(f"/signals/{signal_response.signal.id}/correlate-news")

    assert response.status_code == 200
    assert response.json()["correlationCount"] == 0
