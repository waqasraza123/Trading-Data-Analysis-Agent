from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.daily_briefs.builder import (
    DailyBriefArtifacts,
    DailyBriefBuilder,
    DailyBriefBuildInput,
)
from app.modules.daily_briefs.models import DailyBriefType
from app.modules.daily_briefs.repository import DailyBriefSignalContext
from app.modules.daily_briefs.sections import (
    FORBIDDEN_DAILY_BRIEF_PHRASES,
    sanitize_daily_brief_text,
)
from app.modules.signals.models import Signal
from app.modules.symbols.models import MarketType, Symbol


def test_daily_brief_sanitizes_banned_language() -> None:
    text = sanitize_daily_brief_text(
        "buy now, sell now, enter trade, exit trade, take profit, stop loss, "
        "use leverage, guaranteed profit, win rate, trade alert"
    )

    lowered = text.lower()
    for phrase in FORBIDDEN_DAILY_BRIEF_PHRASES:
        assert phrase not in lowered


def test_daily_brief_builder_classifies_review_and_avoid_sections() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    symbol = Symbol(
        id=symbol_id,
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type=MarketType.FOREX.value,
    )
    bullish_signal = Signal(
        id=uuid4(),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        analysis_run_id=uuid4(),
        timeframe="5m",
        bias="bullish",
        classification_status="signal",
        confidence_score=Decimal("0.8200"),
        confidence_label="high",
        summary="Bullish context",
        no_signal_reason=None,
    )
    no_signal = Signal(
        id=uuid4(),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        analysis_run_id=uuid4(),
        timeframe="5m",
        bias="neutral",
        classification_status="no_signal",
        confidence_score=Decimal("0.3200"),
        confidence_label="low",
        summary="Range conflict",
        no_signal_reason="chop_or_sideways_market",
    )

    built = DailyBriefBuilder().build(
        DailyBriefBuildInput(
            workspace_id=workspace_id,
            brief_type=DailyBriefType.DAILY,
            period_start=datetime(2026, 5, 3, tzinfo=UTC),
            period_end=datetime(2026, 5, 4, tzinfo=UTC),
            timezone="UTC",
            filters_json={},
            max_items=50,
            review_first_limit=20,
            outcome_update_limit=20,
            action_item_limit=30,
        ),
        DailyBriefArtifacts(
            digest_context=None,
            priority_signals=[],
            recent_signals=[
                DailyBriefSignalContext(
                    signal=bullish_signal,
                    symbol=symbol,
                    evidence_count=4,
                    risk_count=0,
                ),
                DailyBriefSignalContext(
                    signal=no_signal,
                    symbol=symbol,
                    evidence_count=2,
                    risk_count=1,
                ),
            ],
            memory_contexts=[],
            provider_health=[],
            latest_candles=[],
            data_quality=[],
            outcomes=[],
            pending_actions=[],
            due_scans=[],
            market_contexts=[],
            journal_contexts=[],
        ),
    )

    sections = built.sections_json
    summaries = " ".join(item.summary for item in built.items).lower()
    assert built.summary_json["counts"]["totalSymbolsReviewed"] == 1
    assert built.summary_json["counts"]["reviewFirstCount"] == 1
    assert built.summary_json["counts"]["avoidConditionCount"] == 1
    assert len(sections["review_first"]) == 1
    assert len(sections["avoid_conditions"]) == 1
    for phrase in FORBIDDEN_DAILY_BRIEF_PHRASES:
        assert phrase not in summaries


def test_daily_brief_empty_artifact_fallback_warns_without_items() -> None:
    workspace_id = uuid4()
    built = DailyBriefBuilder().build(
        DailyBriefBuildInput(
            workspace_id=workspace_id,
            brief_type=DailyBriefType.DAILY,
            period_start=datetime(2026, 5, 3, tzinfo=UTC),
            period_end=datetime(2026, 5, 4, tzinfo=UTC),
            timezone="UTC",
            filters_json={},
            max_items=50,
            review_first_limit=20,
            outcome_update_limit=20,
            action_item_limit=30,
        ),
        DailyBriefArtifacts(
            digest_context=None,
            priority_signals=[],
            recent_signals=[],
            memory_contexts=[],
            provider_health=[],
            latest_candles=[],
            data_quality=[],
            outcomes=[],
            pending_actions=[],
            due_scans=[],
            market_contexts=[],
            journal_contexts=[],
        ),
    )

    assert built.items == []
    assert built.summary_json["counts"]["totalSymbolsReviewed"] == 0
    assert {warning["code"] for warning in built.warnings_json} >= {
        "daily_brief_empty_artifacts",
        "signal_digest_unavailable",
    }
