import struct
import zlib
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.candles.timeframes import Timeframe
from app.modules.chart_screenshots.models import ChartTrendDirection
from app.modules.chart_screenshots.parser import (
    ChartImageBounds,
    ChartImageExtractionConfig,
    build_trend_hypothesis,
    extract_candles_from_png,
)


def test_extract_candles_from_png_returns_bullish_hypothesis() -> None:
    image_bytes = build_test_candlestick_png()
    extraction = extract_candles_from_png(
        image_bytes=image_bytes,
        config=ChartImageExtractionConfig(
            timeframe=Timeframe.FIFTEEN_MINUTES,
            window_start=datetime(2026, 4, 29, 8, 0, tzinfo=UTC),
            price_min=Decimal("100"),
            price_max=Decimal("200"),
            bounds=ChartImageBounds(left=0, top=0, right=119, bottom=79),
        ),
    )

    assert len(extraction.candles) == 3
    assert extraction.confidence > Decimal("0")
    assert extraction.candles[0].timestamp == datetime(2026, 4, 29, 8, 0, tzinfo=UTC)
    assert extraction.candles[1].timestamp == datetime(2026, 4, 29, 8, 15, tzinfo=UTC)
    assert extraction.candles[-1].close > extraction.candles[0].close

    hypothesis = build_trend_hypothesis(extraction.candles, extraction.confidence)

    assert hypothesis.direction == ChartTrendDirection.BULLISH
    assert hypothesis.confidence > Decimal("0")
    assert hypothesis.metrics_json["upwardSteps"] == 2


def build_test_candlestick_png() -> bytes:
    width = 120
    height = 80
    pixels = [[(255, 255, 255) for _ in range(width)] for _ in range(height)]
    draw_candle(pixels, center_x=20, high_y=45, low_y=70, body_top_y=50, body_bottom_y=66)
    draw_candle(pixels, center_x=55, high_y=32, low_y=58, body_top_y=38, body_bottom_y=53)
    draw_candle(pixels, center_x=90, high_y=18, low_y=45, body_top_y=24, body_bottom_y=40)
    rows = bytearray()
    for row in pixels:
        rows.append(0)
        for red, green, blue in row:
            rows.extend([red, green, blue])
    compressed = zlib.compress(bytes(rows))
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )


def draw_candle(
    pixels: list[list[tuple[int, int, int]]],
    center_x: int,
    high_y: int,
    low_y: int,
    body_top_y: int,
    body_bottom_y: int,
) -> None:
    green = (20, 150, 60)
    for y in range(high_y, low_y + 1):
        pixels[y][center_x] = green
    for y in range(body_top_y, body_bottom_y + 1):
        for x in range(center_x - 4, center_x + 5):
            pixels[y][x] = green


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)
