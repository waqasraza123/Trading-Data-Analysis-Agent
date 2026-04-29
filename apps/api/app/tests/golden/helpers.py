import csv
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.analysis.schemas import AnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource
from app.modules.imports.schemas import JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.signals.schemas import SignalClassificationRead
from app.modules.signals.service import SignalClassificationService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace

GOLDEN_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class GoldenExpectation:
    expected_classification_status: str
    expected_bias: str | None
    expected_pattern_type: str | None
    expected_strategy_profile_key: str | None
    confidence_min: Decimal
    confidence_max: Decimal
    expected_no_signal_reason: str | None
    expected_volatility_state: str | None
    expected_trend_state: str | None
    expected_range_state: str | None


@dataclass(frozen=True)
class GoldenRunResult:
    analysis_run: AnalysisRun
    signal_response: SignalClassificationRead | None


def load_golden_candles(fixture_name: str) -> list[RawCandlePayload]:
    fixture_path = GOLDEN_ROOT / "fixtures" / f"{fixture_name}.csv"
    with fixture_path.open(newline="", encoding="utf-8") as fixture_file:
        rows = csv.DictReader(fixture_file)
        return [
            RawCandlePayload(
                timestamp=datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
            for row in rows
        ]


def load_golden_expectation(fixture_name: str) -> GoldenExpectation:
    expectation_path = GOLDEN_ROOT / "expectations" / f"{fixture_name}.json"
    payload = json.loads(expectation_path.read_text(encoding="utf-8"))
    return GoldenExpectation(
        expected_classification_status=str(payload["expected_classification_status"]),
        expected_bias=optional_string(payload["expected_bias"]),
        expected_pattern_type=optional_string(payload["expected_pattern_type"]),
        expected_strategy_profile_key=optional_string(payload["expected_strategy_profile_key"]),
        confidence_min=Decimal(str(payload["confidence_min"])),
        confidence_max=Decimal(str(payload["confidence_max"])),
        expected_no_signal_reason=optional_string(payload["expected_no_signal_reason"]),
        expected_volatility_state=optional_string(payload["expected_volatility_state"]),
        expected_trend_state=optional_string(payload["expected_trend_state"]),
        expected_range_state=optional_string(payload["expected_range_state"]),
    )


async def run_golden_analysis(
    session: AsyncSession,
    fixture_name: str,
    workspace: Workspace,
    user: User,
    symbol: Symbol,
    data_source: DataSource,
) -> GoldenRunResult:
    candles = load_golden_candles(fixture_name)
    await ImportService(session).process_json_import(
        JsonCandleImportRequest(
            workspace_id=workspace.id,
            user_id=user.id,
            source_id=data_source.id,
            symbol_id=symbol.id,
            timeframe=Timeframe.ONE_MINUTE,
            candles=candles,
        )
    )
    analysis_run = await AnalysisService(session).create_historical_run(
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
    if analysis_run.status != AnalysisRunStatus.COMPLETED:
        return GoldenRunResult(analysis_run=analysis_run, signal_response=None)
    signal_response = await SignalClassificationService(session).get_by_analysis_run_id(
        analysis_run.id
    )
    return GoldenRunResult(analysis_run=analysis_run, signal_response=signal_response)


def assert_golden_expectation(
    result: GoldenRunResult,
    expectation: GoldenExpectation,
) -> None:
    if expectation.expected_classification_status == AnalysisRunStatus.INSUFFICIENT_DATA:
        assert result.analysis_run.status == AnalysisRunStatus.INSUFFICIENT_DATA
        assert result.analysis_run.error_code == "insufficient_candle_data"
        return
    assert result.analysis_run.status == AnalysisRunStatus.COMPLETED
    assert result.signal_response is not None
    signal = result.signal_response.signal
    assert signal.classification_status == expectation.expected_classification_status
    if expectation.expected_bias is not None:
        assert signal.bias == expectation.expected_bias
    if expectation.expected_pattern_type is not None:
        assert signal.pattern_type == expectation.expected_pattern_type
    if expectation.expected_strategy_profile_key is not None:
        assert signal.strategy_profile_key == expectation.expected_strategy_profile_key
    assert expectation.confidence_min <= signal.confidence_score <= expectation.confidence_max
    if expectation.expected_no_signal_reason is not None:
        assert signal.no_signal_reason == expectation.expected_no_signal_reason
    if expectation.expected_volatility_state is not None:
        assert signal.volatility_state == expectation.expected_volatility_state
    if expectation.expected_trend_state is not None:
        assert signal.trend_state == expectation.expected_trend_state
    if expectation.expected_range_state is not None:
        assert signal.range_state == expectation.expected_range_state
    assert result.signal_response.evidence
    assert result.signal_response.deterministic_explanation is not None
    assert result.signal_response.deterministic_explanation.short_summary
    assert result.signal_response.deterministic_explanation.full_text
    if signal.strategy_profile_key is not None:
        assert result.signal_response.confidence_components
    if signal.no_signal_reason is not None:
        assert result.signal_response.risk_notes


def optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None
