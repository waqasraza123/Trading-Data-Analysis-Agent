from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.modules.signal_digests.builder import (
    FORBIDDEN_DIGEST_PHRASES,
    SignalDigestArtifacts,
    SignalDigestBuilder,
    SignalDigestBuildInput,
    sanitize_digest_text,
)
from app.modules.signal_digests.models import SignalDigestPriority, SignalDigestType
from app.modules.signal_digests.repository import SignalDigestSignalContext
from app.modules.signals.models import Signal
from app.modules.symbols.models import MarketType, Symbol


def test_signal_digest_sanitizes_blocked_language() -> None:
    text = sanitize_digest_text("buy now for guaranteed profit with leverage")

    lowered = text.lower()
    assert "guaranteed" not in lowered
    assert "profit" not in lowered
    assert "leverage" not in lowered


def test_signal_digest_builder_creates_safe_top_bias_and_no_signal_items() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    analysis_run_id = uuid4()
    bullish_signal = Signal(
        id=uuid4(),
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        analysis_run_id=analysis_run_id,
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
    symbol = Symbol(
        id=symbol_id,
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type=MarketType.FOREX.value,
    )
    built = SignalDigestBuilder().build(
        SignalDigestBuildInput(
            workspace_id=workspace_id,
            digest_type=SignalDigestType.DAILY,
            period_start=datetime(2026, 5, 3, tzinfo=UTC),
            period_end=datetime(2026, 5, 4, tzinfo=UTC),
            timezone="UTC",
            filters_json={},
            max_items=20,
            high_confidence_threshold=Decimal("0.7000"),
            stale_data_priority=SignalDigestPriority.HIGH,
        ),
        SignalDigestArtifacts(
            signals=[
                SignalDigestSignalContext(
                    signal=bullish_signal,
                    symbol=symbol,
                    evidence_count=4,
                    risk_count=0,
                ),
                SignalDigestSignalContext(
                    signal=no_signal,
                    symbol=symbol,
                    evidence_count=2,
                    risk_count=1,
                ),
            ],
            outcomes=[],
            news_context=[],
            pending_actions=[],
            data_quality_warnings=[],
            stale_memory=[],
            quality_reviews=[],
            readiness_reviews=[],
            due_scan_configs=[],
        ),
    )

    summaries = " ".join(item.summary for item in built.items).lower()
    assert built.summary_json["counts"]["totalSignals"] == 2
    assert built.section_counts_json["top_bias"] == 1
    assert built.section_counts_json["no_signal"] == 1
    for phrase in FORBIDDEN_DIGEST_PHRASES:
        assert phrase not in summaries
