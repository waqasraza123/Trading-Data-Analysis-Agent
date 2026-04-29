from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.analysis.models import AnalysisMode, AnalysisRun, AnalysisRunStatus
from app.modules.llm_explanations.grounding import check_explanation_grounding
from app.modules.llm_explanations.input_builder import build_llm_input_payload
from app.modules.llm_explanations.models import (
    LlmExplanationGroundingStatus,
    LlmExplanationSafetyStatus,
)
from app.modules.llm_explanations.schemas import LlmExplanationInputPayload
from app.modules.llm_explanations.service import LlmExplanationService
from app.modules.signals.models import (
    Signal,
    SignalBias,
    SignalClassificationStatus,
    SignalConfidenceLabel,
)


def test_llm_input_includes_structured_news_correlation_when_present() -> None:
    payload = input_payload(
        [
            {
                "eventTitle": "USD CPI Release",
                "eventType": "economic_calendar",
                "eventTime": "2026-04-29T12:26:00+00:00",
                "currency": "USD",
                "asset": None,
                "importance": "high",
                "correlationLabel": "strong",
                "correlationScore": "0.8123",
                "timeDeltaMinutes": "4.0000",
                "directionAlignment": "aligned",
                "volatilityReaction": "spike",
                "reason": "Strong possible correlation detected.",
            }
        ]
    )

    assert payload.news_correlations == [
        {
            "eventTitle": "USD CPI Release",
            "eventType": "economic_calendar",
            "eventTime": "2026-04-29T12:26:00+00:00",
            "currency": "USD",
            "asset": None,
            "importance": "high",
            "correlationLabel": "strong",
            "correlationScore": "0.8123",
            "timeDeltaMinutes": "4.0000",
            "directionAlignment": "aligned",
            "volatilityReaction": "spike",
            "reason": "Strong possible correlation detected.",
        }
    ]


def test_llm_input_excludes_news_when_no_correlation_exists() -> None:
    payload = input_payload([])

    assert payload.news_correlations == []


def test_grounding_blocks_news_mentions_without_input_news() -> None:
    result = check_explanation_grounding(
        input_payload([]).model_dump(mode="json"),
        "The CPI news happened near the signal window.",
    )

    assert result.status == LlmExplanationGroundingStatus.FAILED
    assert "without persisted news correlation evidence" in result.issues[0]


def test_grounding_blocks_news_causation_claims() -> None:
    result = check_explanation_grounding(
        input_payload(
            [
                {
                    "eventTitle": "USD CPI Release",
                    "eventType": "economic_calendar",
                    "eventTime": "2026-04-29T12:26:00+00:00",
                    "currency": "USD",
                    "asset": None,
                    "importance": "high",
                    "correlationLabel": "strong",
                    "correlationScore": "0.8123",
                    "timeDeltaMinutes": "4.0000",
                    "directionAlignment": "aligned",
                    "volatilityReaction": "spike",
                    "reason": "Strong possible correlation detected.",
                }
            ]
        ).model_dump(mode="json"),
        "The high USD event definitely caused the move.",
    )

    assert result.status == LlmExplanationGroundingStatus.FAILED
    assert "output states causation from correlation" in result.issues


def test_grounding_allows_cautious_news_correlation_language() -> None:
    result = check_explanation_grounding(
        input_payload(
            [
                {
                    "eventTitle": "USD CPI Release",
                    "eventType": "economic_calendar",
                    "eventTime": "2026-04-29T12:26:00+00:00",
                    "currency": "USD",
                    "asset": None,
                    "importance": "high",
                    "correlationLabel": "strong",
                    "correlationScore": "0.8123",
                    "timeDeltaMinutes": "4.0000",
                    "directionAlignment": "aligned",
                    "volatilityReaction": "spike",
                    "reason": "Strong possible correlation detected.",
                }
            ]
        ).model_dump(mode="json"),
        "The high USD event happened near the signal window and may have contributed.",
    )

    assert result.status == LlmExplanationGroundingStatus.GROUNDED
    assert result.issues == []


def test_llm_validation_uses_fallback_for_ungrounded_news_causation() -> None:
    service = LlmExplanationService(
        cast(AsyncSession, object()),
        settings=Settings(_env_file=None, llm_explanations_enabled=True),
    )
    result = service.validate_output(
        input_payload(
            [
                {
                    "eventTitle": "USD CPI Release",
                    "eventType": "economic_calendar",
                    "eventTime": "2026-04-29T12:26:00+00:00",
                    "currency": "USD",
                    "asset": None,
                    "importance": "high",
                    "correlationLabel": "strong",
                    "correlationScore": "0.8123",
                    "timeDeltaMinutes": "4.0000",
                    "directionAlignment": "aligned",
                    "volatilityReaction": "spike",
                    "reason": "Strong possible correlation detected.",
                }
            ]
        ),
        "The high USD event caused the move.",
        "Fallback deterministic explanation.",
    )

    assert result.output_text == "Fallback deterministic explanation."
    assert result.safety_status == LlmExplanationSafetyStatus.FALLBACK_USED
    assert result.grounding_status == LlmExplanationGroundingStatus.FAILED


def input_payload(news_correlations: list[dict[str, object]]) -> LlmExplanationInputPayload:
    return build_llm_input_payload(
        signal=signal_row(),
        run=run_row(),
        symbol="EURUSD",
        confidence_components=[],
        evidence=[],
        risk_notes=[],
        deterministic_explanation=None,
        feature_snapshot=None,
        indicator_snapshot=None,
        news_correlations=news_correlations,
    )


def run_row() -> AnalysisRun:
    return AnalysisRun(
        id=uuid4(),
        workspace_id=uuid4(),
        user_id=None,
        symbol_id=uuid4(),
        source_id=None,
        timeframe="1m",
        start_time=datetime(2026, 4, 29, 12, 30, tzinfo=UTC),
        end_time=datetime(2026, 4, 29, 12, 45, tzinfo=UTC),
        analysis_mode=AnalysisMode.HISTORICAL.value,
        include_partial_live_candle=False,
        include_news_correlation=True,
        include_ai_explanation=True,
        status=AnalysisRunStatus.COMPLETED.value,
        engine_version="test",
        rule_set_version="test",
    )


def signal_row() -> Signal:
    return Signal(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="1m",
        bias=SignalBias.BULLISH.value,
        classification_status=SignalClassificationStatus.SIGNAL.value,
        confidence_score=Decimal("0.8000"),
        confidence_label=SignalConfidenceLabel.HIGH.value,
        pips_moved=Decimal("10"),
        tick_moved=Decimal("100"),
        movement_direction=SignalBias.BULLISH.value,
        movement_quality="efficient",
        volatility_state="spike",
        trend_state="short_term_uptrend",
        range_state="range_break",
        summary="Test signal",
    )
