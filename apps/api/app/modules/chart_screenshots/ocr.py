from dataclasses import dataclass, field
from decimal import Decimal
from importlib import import_module
from typing import Any, Protocol, cast

from app.core.errors import AppError
from app.modules.chart_screenshots.types import ChartOcrStatus


@dataclass(frozen=True)
class OcrPoint:
    x: int
    y: int


@dataclass(frozen=True)
class OcrTextBox:
    text: str
    confidence: Decimal | None
    vertices: list[OcrPoint]


@dataclass(frozen=True)
class ChartOcrResult:
    status: ChartOcrStatus
    provider: str
    confidence: Decimal | None
    text_boxes: list[OcrTextBox]
    provider_payload_json: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)


class ChartOcrProvider(Protocol):
    def extract_text(self, image_bytes: bytes, timeout_seconds: float) -> ChartOcrResult: ...


class GoogleVisionChartOcrProvider:
    provider = "google_vision"

    def extract_text(self, image_bytes: bytes, timeout_seconds: float) -> ChartOcrResult:
        try:
            vision = import_module("google.cloud.vision")
            json_format = import_module("google.protobuf.json_format")
        except ImportError as error:
            raise AppError(
                503,
                "chart_ocr_provider_unavailable",
                "Google Vision OCR dependencies are not installed",
            ) from error
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image, timeout=timeout_seconds)
        if response.error.message:
            raise AppError(502, "chart_ocr_failed", response.error.message)
        payload = cast(
            dict[str, Any],
            json_format.MessageToDict(response._pb, preserving_proto_field_name=True),
        )
        annotations = list(response.text_annotations)
        text_boxes = [
            build_text_box(annotation)
            for annotation in annotations[1:]
            if annotation.description.strip()
        ]
        confidence = average_confidence(text_boxes)
        return ChartOcrResult(
            status=ChartOcrStatus.SUCCEEDED if text_boxes else ChartOcrStatus.FAILED,
            provider=self.provider,
            confidence=confidence,
            text_boxes=text_boxes,
            provider_payload_json=payload,
            warnings=[] if text_boxes else ["OCR did not return chart text boxes"],
        )


class EmptyChartOcrProvider:
    provider = "mock"

    def extract_text(self, image_bytes: bytes, timeout_seconds: float) -> ChartOcrResult:
        return ChartOcrResult(
            status=ChartOcrStatus.FAILED,
            provider=self.provider,
            confidence=Decimal("0.0000"),
            text_boxes=[],
            provider_payload_json={"textAnnotations": []},
            warnings=["Mock OCR provider returned no text boxes"],
        )


def get_chart_ocr_provider(provider_name: str) -> ChartOcrProvider:
    if provider_name == "google_vision":
        return GoogleVisionChartOcrProvider()
    if provider_name == "mock":
        return EmptyChartOcrProvider()
    raise AppError(422, "unsupported_chart_ocr_provider", "Unsupported chart OCR provider")


def build_text_box(annotation: object) -> OcrTextBox:
    annotation_object = cast(Any, annotation)
    vertices = [
        OcrPoint(x=int(getattr(vertex, "x", 0)), y=int(getattr(vertex, "y", 0)))
        for vertex in annotation_object.bounding_poly.vertices
    ]
    confidence_value = getattr(annotation_object, "confidence", None)
    confidence = (
        Decimal(str(confidence_value)).quantize(Decimal("0.0001"))
        if confidence_value is not None
        else None
    )
    return OcrTextBox(
        text=str(annotation_object.description).strip(),
        confidence=confidence,
        vertices=vertices,
    )


def average_confidence(text_boxes: list[OcrTextBox]) -> Decimal | None:
    confidence_values = [box.confidence for box in text_boxes if box.confidence is not None]
    if not confidence_values:
        return None
    return (sum(confidence_values, Decimal("0")) / Decimal(len(confidence_values))).quantize(
        Decimal("0.0001")
    )


def serialize_ocr_result(result: ChartOcrResult) -> dict[str, Any]:
    return {
        "status": result.status.value,
        "provider": result.provider,
        "confidence": str(result.confidence) if result.confidence is not None else None,
        "textBoxes": [
            {
                "text": box.text,
                "confidence": str(box.confidence) if box.confidence is not None else None,
                "vertices": [{"x": vertex.x, "y": vertex.y} for vertex in box.vertices],
            }
            for box in result.text_boxes
        ],
        "providerPayload": result.provider_payload_json,
        "warnings": result.warnings,
    }
