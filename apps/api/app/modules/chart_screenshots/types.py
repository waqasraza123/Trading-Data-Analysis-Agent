from enum import StrEnum


class ChartCalibrationMode(StrEnum):
    MANUAL = "manual"
    OCR = "ocr"
    MANUAL_WITH_OCR_AUDIT = "manual_with_ocr_audit"


class ChartImageType(StrEnum):
    CANDLESTICK = "candlestick"
    OHLC_BAR = "ohlc_bar"
    LINE_AREA = "line_area"
    UNKNOWN = "unknown"


class ChartOcrStatus(StrEnum):
    DISABLED = "disabled"
    NOT_REQUESTED = "not_requested"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
