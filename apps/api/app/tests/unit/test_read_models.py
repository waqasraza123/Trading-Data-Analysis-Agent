from decimal import Decimal
from uuid import uuid4

from app.modules.read_models.builders import ReadModelBuilder
from app.modules.read_models.repository import SignalCardArtifacts, SymbolReadModelArtifacts
from app.modules.signals.models import Signal


def test_signal_card_builder_degrades_without_optional_artifacts() -> None:
    signal = Signal(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="5m",
        bias="bullish",
        pattern_type="breakout",
        classification_status="signal",
        confidence_score=Decimal("0.7100"),
        confidence_label="high",
        summary="Stored deterministic setup summary.",
    )
    builder = ReadModelBuilder()

    card = builder.build_signal_card(SignalCardArtifacts(signal=signal, analysis_run=None), "v1")

    assert card.signal_id == signal.id
    assert card.classification_status == "signal"
    assert card.priority_label is None
    assert card.warning_summary_json["count"] == 1
    assert "bullish" in card.searchable_text


def test_symbol_read_model_builder_preserves_snapshot_boundaries() -> None:
    workspace_id = uuid4()
    symbol_id = uuid4()
    builder = ReadModelBuilder()

    model = builder.build_symbol_model(
        SymbolReadModelArtifacts(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=None,
            timeframe="15m",
        ),
        "v1",
    )

    assert model.workspace_id == workspace_id
    assert model.symbol_id == symbol_id
    assert model.latest_signal_id is None
    assert model.warning_count == 1
    assert model.summary_json["sourceArtifacts"]["marketMemoryId"] is None
