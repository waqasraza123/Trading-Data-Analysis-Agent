from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import Settings
from app.modules.candles.models import Candle
from app.modules.equity_data.adapters.base import EquityProviderContext
from app.modules.equity_data.adapters.mock import MockEquityDataProvider
from app.modules.equity_data.normalizer import normalize_ticker, safe_reference
from app.modules.equity_research.repository import EquityResearchArtifacts
from app.modules.equity_research.scoring import EquitySwingScorer, EquitySwingScoringInput


def test_normalize_ticker_uppercases_and_trims() -> None:
    assert normalize_ticker(" aapl ") == "AAPL"


def test_safe_reference_redacts_secret_like_keys() -> None:
    payload = {"api_key": "secret-value", "nested": {"authorization": "bearer value"}}

    redacted = safe_reference(payload)

    assert redacted["api_key"] == "[redacted]"
    assert redacted["nested"] == {"authorization": "[redacted]"}


@pytest.mark.asyncio
async def test_mock_provider_imports_deterministic_universe() -> None:
    provider = MockEquityDataProvider()

    result = await provider.import_universe(
        EquityProviderContext(
            workspace_id=str(uuid4()),
            credential_ref_id=None,
            external_requests_enabled=False,
            timeout_seconds=20,
        ),
        {"filters": {"limit": 2}},
    )

    assert result.status == "completed"
    assert [item.ticker for item in result.metadata] == ["AAPL", "MSFT"]
    assert result.metadata[0].average_volume == Decimal("52000000")


def test_equity_scorer_marks_missing_fundamentals_context() -> None:
    settings = Settings()
    scorer = EquitySwingScorer(settings)
    now = datetime.now(UTC)

    draft = scorer.score(
        EquitySwingScoringInput(
            ticker="AAPL",
            timeframe="1d",
            candles=candle_series(now),
            artifacts=EquityResearchArtifacts(),
            average_volume=Decimal("1200000"),
            profile=scorer.profile("continuation_momentum"),
            evaluated_at=now,
            source_id_provided=True,
        )
    )

    assert any(
        item["message"] == "Fundamentals context unavailable."
        for item in draft.evidence_json
    )
    assert any(
        item["message"] == "Average volume context available."
        for item in draft.evidence_json
    )


def test_new_equity_data_files_avoid_restricted_phrases() -> None:
    api_root = Path(__file__).resolve().parents[3]
    paths = [
        api_root / "app/modules/equity_data",
        api_root / "app/modules/equity_research/scoring.py",
    ]
    text = "\n".join(
        path.read_text()
        for root in paths
        for path in ([root] if root.is_file() else root.rglob("*.py"))
    ).lower()

    for phrase in [
        "buy now",
        "sell now",
        "enter trade",
        "exit trade",
        "take profit",
        "stop loss",
        "use leverage",
        "guaranteed",
        "profit",
        "win rate",
        "ready to trade",
        "trade alert",
    ]:
        assert phrase not in text


def candle_series(now: datetime, count: int = 80) -> list[Candle]:
    workspace_id = uuid4()
    symbol_id = uuid4()
    source_id = uuid4()
    candles = []
    for index in range(count):
        base = Decimal("100") + Decimal(index)
        candles.append(
            Candle(
                id=uuid4(),
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                source_id=source_id,
                timeframe="1d",
                timestamp=now.replace(microsecond=0),
                open=base,
                high=base + Decimal("1"),
                low=base - Decimal("1"),
                close=base,
                volume=Decimal("600000") + Decimal(index),
                is_final=True,
            )
        )
    return candles
