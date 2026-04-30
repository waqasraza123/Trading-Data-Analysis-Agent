import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from app.modules.chart_screenshots.ocr import ChartOcrResult, OcrTextBox
from app.modules.chart_screenshots.types import ChartOcrStatus

PRICE_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?")
DATETIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?")


@dataclass(frozen=True)
class AxisCalibration:
    window_start: datetime | None
    price_min: Decimal | None
    price_max: Decimal | None
    status: ChartOcrStatus
    confidence: Decimal | None
    metadata_json: dict[str, object]
    warnings: list[str] = field(default_factory=list)


def build_axis_calibration(
    ocr_result: ChartOcrResult | None,
    image_width: int,
    image_height: int,
    manual_window_start: datetime | None,
    manual_price_min: Decimal | None,
    manual_price_max: Decimal | None,
) -> AxisCalibration:
    if ocr_result is None:
        return AxisCalibration(
            window_start=manual_window_start,
            price_min=manual_price_min,
            price_max=manual_price_max,
            status=ChartOcrStatus.NOT_REQUESTED,
            confidence=None,
            metadata_json={"source": "manual"},
            warnings=[],
        )
    price_values = extract_price_values(ocr_result.text_boxes, image_width)
    inferred_price_min = min(price_values) if len(price_values) >= 2 else None
    inferred_price_max = max(price_values) if len(price_values) >= 2 else None
    inferred_window_start = extract_window_start(ocr_result.text_boxes, image_height)
    price_min = manual_price_min or inferred_price_min
    price_max = manual_price_max or inferred_price_max
    window_start = manual_window_start or inferred_window_start
    warnings = list(ocr_result.warnings)
    if (
        (manual_price_min is None or manual_price_max is None)
        and (inferred_price_min is None or inferred_price_max is None)
    ):
        warnings.append("OCR could not infer a complete price axis")
    if manual_window_start is None and inferred_window_start is None:
        warnings.append("OCR could not infer a complete time axis")
    status = (
        ChartOcrStatus.SUCCEEDED
        if price_min is not None and price_max is not None and window_start is not None
        else ChartOcrStatus.PARTIAL
    )
    return AxisCalibration(
        window_start=window_start,
        price_min=price_min,
        price_max=price_max,
        status=status,
        confidence=ocr_result.confidence,
        metadata_json={
            "source": "ocr",
            "status": status.value,
            "confidence": str(ocr_result.confidence) if ocr_result.confidence is not None else None,
            "manualWindowStartProvided": manual_window_start is not None,
            "manualPriceRangeProvided": (
                manual_price_min is not None and manual_price_max is not None
            ),
            "inferredPriceMin": str(inferred_price_min) if inferred_price_min is not None else None,
            "inferredPriceMax": str(inferred_price_max) if inferred_price_max is not None else None,
            "inferredWindowStart": (
                inferred_window_start.isoformat() if inferred_window_start is not None else None
            ),
        },
        warnings=warnings,
    )


def extract_price_values(text_boxes: list[OcrTextBox], image_width: int) -> list[Decimal]:
    values: list[Decimal] = []
    for box in text_boxes:
        center_x, _ = box_center(box)
        if center_x < image_width * 0.55:
            continue
        if ":" in box.text or "-" in box.text:
            continue
        for match in PRICE_RE.findall(box.text):
            try:
                value = Decimal(match.replace(",", ""))
            except InvalidOperation:
                continue
            if value > 0:
                values.append(value)
    return sorted(set(values))


def extract_window_start(text_boxes: list[OcrTextBox], image_height: int) -> datetime | None:
    bottom_boxes = [
        box
        for box in text_boxes
        if box_center(box)[1] >= image_height * 0.55
    ]
    candidates: list[tuple[int, datetime]] = []
    for box in bottom_boxes:
        parsed = parse_datetime_text(box.text)
        if parsed is not None:
            center_x, _ = box_center(box)
            candidates.append((center_x, parsed))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def parse_datetime_text(value: str) -> datetime | None:
    match = DATETIME_RE.search(value.strip())
    if match is None:
        return None
    normalized = match.group(0).replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def box_center(box: OcrTextBox) -> tuple[int, int]:
    if not box.vertices:
        return (0, 0)
    return (
        int(sum(vertex.x for vertex in box.vertices) / len(box.vertices)),
        int(sum(vertex.y for vertex in box.vertices) / len(box.vertices)),
    )
