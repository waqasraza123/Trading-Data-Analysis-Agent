from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.modules.candles.models import Candle
from app.modules.equity_research.models import (
    EquitySwingCandidateStatus,
    EquitySwingSetupQualityLabel,
)
from app.modules.equity_research.repository import EquityResearchArtifacts
from app.modules.equity_research.scoring import EquitySwingScorer, EquitySwingScoringInput
from app.modules.equity_research.service import EquityResearchService
from app.modules.symbols.models import MarketType, Symbol


def test_equity_scorer_marks_strong_context_for_clean_momentum() -> None:
    settings = Settings()
    scorer = EquitySwingScorer(settings)
    now = datetime.now(UTC)

    draft = scorer.score(
        EquitySwingScoringInput(
            ticker="AAPL",
            timeframe="1d",
            candles=candle_series(now=now, days_old=0),
            artifacts=EquityResearchArtifacts(),
            average_volume=Decimal("1200000"),
            min_average_volume=Decimal("500000"),
            profile=scorer.profile("continuation_momentum"),
            evaluated_at=now,
            source_id_provided=True,
        )
    )

    assert draft.candidate_status == EquitySwingCandidateStatus.CANDIDATE
    assert draft.setup_quality_label == EquitySwingSetupQualityLabel.STRONG_CONTEXT
    assert draft.setup_quality_score >= Decimal("0.7500")


def test_equity_scorer_marks_stale_data() -> None:
    settings = Settings()
    scorer = EquitySwingScorer(settings)
    now = datetime.now(UTC)

    draft = scorer.score(
        EquitySwingScoringInput(
            ticker="MSFT",
            timeframe="1d",
            candles=candle_series(now=now, days_old=21),
            artifacts=EquityResearchArtifacts(),
            average_volume=Decimal("900000"),
            profile=scorer.profile("continuation_momentum"),
            evaluated_at=now,
            source_id_provided=True,
        )
    )

    assert draft.candidate_status == EquitySwingCandidateStatus.STALE_DATA
    assert any(note["code"] == "data_stale" for note in draft.risk_notes_json)


def test_equity_scorer_handles_missing_optional_artifacts() -> None:
    settings = Settings()
    scorer = EquitySwingScorer(settings)
    now = datetime.now(UTC)

    draft = scorer.score(
        EquitySwingScoringInput(
            ticker="NVDA",
            timeframe="4h",
            candles=candle_series(now=now, days_old=0, step=timedelta(hours=4)),
            artifacts=EquityResearchArtifacts(),
            average_volume=None,
            profile=scorer.profile("constructive_pullback"),
            evaluated_at=now,
            source_id_provided=False,
        )
    )

    assert draft.setup_quality_score >= Decimal("0")
    assert any(note["code"] == "setup_context_missing" for note in draft.risk_notes_json)
    assert any(note["code"] == "source_not_pinned" for note in draft.risk_notes_json)


def test_equity_candidate_text_avoids_restricted_phrases() -> None:
    settings = Settings()
    scorer = EquitySwingScorer(settings)
    now = datetime.now(UTC)

    draft = scorer.score(
        EquitySwingScoringInput(
            ticker="META",
            timeframe="1d",
            candles=candle_series(now=now, days_old=0),
            artifacts=EquityResearchArtifacts(),
            average_volume=Decimal("900000"),
            profile=scorer.profile("breakout_retest"),
            evaluated_at=now,
            source_id_provided=True,
        )
    )
    serialized = f"{draft.evidence_json} {draft.risk_notes_json}".lower()

    for phrase in [
        "buy now",
        "sell now",
        "enter trade",
        "exit trade",
        "take profit",
        "stop loss",
        "use leverage",
        "guaranteed",
        "risk-free",
        "win rate",
        "ready to trade",
        "trading alert",
    ]:
        assert phrase not in serialized


@pytest.mark.asyncio
async def test_equity_universe_member_validation_requires_stock_symbol() -> None:
    service = EquityResearchService(cast(AsyncSession, object()))
    service.symbol_repository = FakeSymbolRepository(
        symbol_row(market_type=MarketType.CRYPTO.value)
    )

    with pytest.raises(AppError) as error:
        await service.validate_stock_symbol(uuid4())

    assert error.value.code == "equity_symbol_required"


def candle_series(
    now: datetime,
    days_old: int,
    count: int = 80,
    step: timedelta = timedelta(days=1),
) -> list[Candle]:
    source_id = uuid4()
    workspace_id = uuid4()
    symbol_id = uuid4()
    end_time = now - timedelta(days=days_old)
    start_time = end_time - (step * (count - 1))
    candles: list[Candle] = []
    for index in range(count):
        timestamp = start_time + (step * index)
        base = Decimal("100") + Decimal(index) * Decimal("0.65")
        candles.append(
            Candle(
                id=uuid4(),
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                source_id=source_id,
                timeframe="1d",
                timestamp=timestamp,
                open=base - Decimal("0.20"),
                high=base + Decimal("1.00"),
                low=base - Decimal("0.70"),
                close=base,
                volume=Decimal("600000") + Decimal(index * 5000),
                is_final=True,
            )
        )
    return candles


def symbol_row(market_type: str) -> Symbol:
    return Symbol(
        id=uuid4(),
        symbol="BTCUSDT" if market_type == MarketType.CRYPTO.value else "AAPL",
        display_name="Fixture Symbol",
        market_type=market_type,
        base_asset=None,
        quote_asset=None,
        pip_size=None,
        tick_size=Decimal("0.01"),
        price_precision=2,
        quantity_precision=0,
        is_active=True,
    )


class FakeSymbolRepository:
    def __init__(self, symbol: Symbol | None) -> None:
        self.symbol = symbol

    async def get_by_id(self, symbol_id: UUID) -> Symbol | None:
        return self.symbol
