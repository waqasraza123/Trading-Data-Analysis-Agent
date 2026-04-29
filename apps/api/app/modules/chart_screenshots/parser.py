import struct
import zlib
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from app.core.errors import AppError
from app.modules.candles.timeframes import Timeframe, timeframe_duration
from app.modules.chart_screenshots.models import ChartTrendDirection
from app.modules.chart_screenshots.schemas import ChartScreenshotCandle

CHART_SCREENSHOT_PARSER_NAME = "manual_chart_screenshot_extraction"
CHART_SCREENSHOT_PARSER_VERSION = "0.1.0"
CHART_SCREENSHOT_IMAGE_PARSER_NAME = "deterministic_png_candle_extraction"
CHART_SCREENSHOT_IMAGE_PARSER_VERSION = "0.1.0"
MIN_DIRECTIONAL_MOVE = Decimal("0.001")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_DETECTED_CANDLES = 3
MAX_DETECTED_CANDLES = 240


@dataclass(frozen=True)
class ChartImageBounds:
    left: int
    top: int
    right: int
    bottom: int


@dataclass(frozen=True)
class ChartImageExtractionConfig:
    timeframe: Timeframe
    window_start: datetime
    price_min: Decimal
    price_max: Decimal
    bounds: ChartImageBounds | None


@dataclass(frozen=True)
class RgbPixel:
    red: int
    green: int
    blue: int


@dataclass(frozen=True)
class DecodedPngImage:
    width: int
    height: int
    pixels: list[list[RgbPixel]]


@dataclass(frozen=True)
class PixelCluster:
    left: int
    right: int
    high_y: int
    low_y: int
    body_top_y: int
    body_bottom_y: int
    direction: ChartTrendDirection


@dataclass(frozen=True)
class ChartImageExtractionResult:
    candles: list[ChartScreenshotCandle]
    confidence: Decimal
    parser_metadata_json: dict[str, object]
    warnings: list[str]


@dataclass(frozen=True)
class ChartTrendHypothesis:
    direction: ChartTrendDirection
    confidence: Decimal
    metrics_json: dict[str, object]
    warnings: list[str]


def build_trend_hypothesis(
    candles: list[ChartScreenshotCandle],
    extraction_confidence: Decimal,
) -> ChartTrendHypothesis:
    sorted_candles = sorted(candles, key=lambda candle: candle.timestamp)
    warnings: list[str] = []
    if len(sorted_candles) < 3:
        return ChartTrendHypothesis(
            direction=ChartTrendDirection.UNCLEAR,
            confidence=Decimal("0.0000"),
            metrics_json={"reason": "too_few_candles"},
            warnings=["At least three extracted candles are required for a trend hypothesis"],
        )

    first_close = sorted_candles[0].close
    last_close = sorted_candles[-1].close
    move_ratio = (last_close - first_close) / first_close
    close_deltas = [
        sorted_candles[index].close - sorted_candles[index - 1].close
        for index in range(1, len(sorted_candles))
    ]
    upward_steps = sum(1 for delta in close_deltas if delta > 0)
    downward_steps = sum(1 for delta in close_deltas if delta < 0)
    flat_steps = len(close_deltas) - upward_steps - downward_steps
    directional_steps = max(upward_steps, downward_steps)
    consistency = Decimal(directional_steps) / Decimal(len(close_deltas))
    magnitude = min(abs(move_ratio) * Decimal("20"), Decimal("1"))
    confidence = ((consistency * Decimal("0.60")) + (magnitude * Decimal("0.40")))
    confidence = (confidence * extraction_confidence).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )

    if abs(move_ratio) < MIN_DIRECTIONAL_MOVE:
        direction = ChartTrendDirection.NEUTRAL
    elif move_ratio > 0:
        direction = ChartTrendDirection.BULLISH
    else:
        direction = ChartTrendDirection.BEARISH

    if extraction_confidence < Decimal("0.5"):
        warnings.append("Extraction confidence is low; treat the trend hypothesis as provisional")
    if consistency < Decimal("0.5"):
        warnings.append("Extracted candle closes are mixed; trend direction is weak")

    return ChartTrendHypothesis(
        direction=direction,
        confidence=confidence,
        metrics_json={
            "firstClose": str(first_close),
            "lastClose": str(last_close),
            "moveRatio": str(move_ratio.quantize(Decimal("0.000001"))),
            "upwardSteps": upward_steps,
            "downwardSteps": downward_steps,
            "flatSteps": flat_steps,
            "closeConsistency": str(consistency.quantize(Decimal("0.0001"))),
        },
        warnings=warnings,
    )


def extract_candles_from_png(
    image_bytes: bytes,
    config: ChartImageExtractionConfig,
) -> ChartImageExtractionResult:
    image = decode_png(image_bytes)
    bounds = config.bounds or detect_chart_bounds(image)
    validate_bounds(bounds, image)
    foreground_mask = build_foreground_mask(image, bounds)
    clusters = detect_pixel_clusters(image=image, bounds=bounds, foreground_mask=foreground_mask)
    if len(clusters) < MIN_DETECTED_CANDLES:
        raise AppError(
            422,
            "chart_image_candles_not_detected",
            "At least three candle shapes could not be detected in the chart image",
        )
    if len(clusters) > MAX_DETECTED_CANDLES:
        clusters = clusters[-MAX_DETECTED_CANDLES:]
    candles = clusters_to_candles(clusters=clusters, bounds=bounds, config=config)
    confidence = calculate_image_extraction_confidence(clusters=clusters, bounds=bounds)
    warnings: list[str] = []
    if confidence < Decimal("0.5000"):
        warnings.append("Detected chart geometry is sparse; verify extracted candles manually")
    if config.bounds is None:
        warnings.append("Chart bounds were inferred from image pixels")
    return ChartImageExtractionResult(
        candles=candles,
        confidence=confidence,
        parser_metadata_json={
            "imageWidth": image.width,
            "imageHeight": image.height,
            "chartBounds": {
                "left": bounds.left,
                "top": bounds.top,
                "right": bounds.right,
                "bottom": bounds.bottom,
            },
            "detectedCandleCount": len(candles),
        },
        warnings=warnings,
    )


def decode_png(image_bytes: bytes) -> DecodedPngImage:
    if not image_bytes.startswith(PNG_SIGNATURE):
        raise AppError(422, "unsupported_chart_image", "Chart image must be an 8-bit PNG")
    offset = len(PNG_SIGNATURE)
    width: int | None = None
    height: int | None = None
    color_type: int | None = None
    idat_chunks: list[bytes] = []
    while offset + 8 <= len(image_bytes):
        chunk_length = struct.unpack(">I", image_bytes[offset : offset + 4])[0]
        chunk_type = image_bytes[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_length
        if chunk_end + 4 > len(image_bytes):
            raise AppError(422, "invalid_chart_png", "PNG chunk data is truncated")
        chunk_data = image_bytes[chunk_start:chunk_end]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB",
                chunk_data,
            )
            if bit_depth != 8 or color_type not in {0, 2, 6} or interlace != 0:
                raise AppError(
                    422,
                    "unsupported_chart_image",
                    "Only non-interlaced 8-bit grayscale, RGB, or RGBA PNG charts are supported",
                )
        elif chunk_type == b"IDAT":
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            break
        offset = chunk_end + 4
    if width is None or height is None or color_type is None or not idat_chunks:
        raise AppError(422, "invalid_chart_png", "PNG image is missing required data")
    decompressed = zlib.decompress(b"".join(idat_chunks))
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    row_length = width * channels
    expected_length = height * (row_length + 1)
    if len(decompressed) != expected_length:
        raise AppError(422, "invalid_chart_png", "PNG pixel data has an unexpected size")
    rows: list[bytes] = []
    cursor = 0
    previous = bytes(row_length)
    for _ in range(height):
        filter_type = decompressed[cursor]
        cursor += 1
        row = bytearray(decompressed[cursor : cursor + row_length])
        cursor += row_length
        unfiltered = unfilter_png_row(row, previous, filter_type, channels)
        rows.append(bytes(unfiltered))
        previous = bytes(unfiltered)
    pixels: list[list[RgbPixel]] = []
    for row_bytes in rows:
        pixel_row: list[RgbPixel] = []
        for x in range(width):
            position = x * channels
            if color_type == 0:
                value = row_bytes[position]
                pixel_row.append(RgbPixel(value, value, value))
            else:
                pixel_row.append(
                    RgbPixel(
                        row_bytes[position],
                        row_bytes[position + 1],
                        row_bytes[position + 2],
                    )
                )
        pixels.append(pixel_row)
    return DecodedPngImage(width=width, height=height, pixels=pixels)


def unfilter_png_row(
    row: bytearray,
    previous: bytes,
    filter_type: int,
    bytes_per_pixel: int,
) -> bytearray:
    if filter_type == 0:
        return row
    for index, value in enumerate(row):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index]
        up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = up
        elif filter_type == 3:
            predictor = (left + up) // 2
        elif filter_type == 4:
            predictor = paeth_predictor(left, up, up_left)
        else:
            raise AppError(422, "invalid_chart_png", "PNG uses an invalid row filter")
        row[index] = (value + predictor) & 0xFF
    return row


def paeth_predictor(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    up_left_distance = abs(estimate - up_left)
    if left_distance <= up_distance and left_distance <= up_left_distance:
        return left
    if up_distance <= up_left_distance:
        return up
    return up_left


def detect_chart_bounds(image: DecodedPngImage) -> ChartImageBounds:
    full_bounds = ChartImageBounds(left=0, top=0, right=image.width - 1, bottom=image.height - 1)
    mask = build_foreground_mask(image, full_bounds)
    active_points = [
        (x, y)
        for y in range(image.height)
        for x in range(image.width)
        if mask[y][x]
    ]
    if not active_points:
        raise AppError(
            422,
            "chart_image_foreground_not_detected",
            "Chart image does not contain detectable candle pixels",
        )
    left = max(min(x for x, _ in active_points) - 2, 0)
    right = min(max(x for x, _ in active_points) + 2, image.width - 1)
    top = max(min(y for _, y in active_points) - 2, 0)
    bottom = min(max(y for _, y in active_points) + 2, image.height - 1)
    return ChartImageBounds(left=left, top=top, right=right, bottom=bottom)


def validate_bounds(bounds: ChartImageBounds, image: DecodedPngImage) -> None:
    if (
        bounds.left < 0
        or bounds.top < 0
        or bounds.right >= image.width
        or bounds.bottom >= image.height
        or bounds.left >= bounds.right
        or bounds.top >= bounds.bottom
    ):
        raise AppError(422, "invalid_chart_bounds", "Chart image bounds are invalid")


def build_foreground_mask(
    image: DecodedPngImage,
    bounds: ChartImageBounds,
) -> list[list[bool]]:
    background = estimate_background_color(image)
    mask = [[False for _ in range(image.width)] for _ in range(image.height)]
    for y in range(bounds.top, bounds.bottom + 1):
        for x in range(bounds.left, bounds.right + 1):
            pixel = image.pixels[y][x]
            distance = color_distance(pixel, background)
            is_colored_candle = (
                abs(pixel.green - pixel.red) >= 35
                and max(pixel.red, pixel.green) >= 80
                and pixel.blue <= max(pixel.red, pixel.green) + 20
            )
            mask[y][x] = distance >= 90 or is_colored_candle
    return mask


def estimate_background_color(image: DecodedPngImage) -> RgbPixel:
    samples: list[RgbPixel] = []
    for x in range(image.width):
        samples.append(image.pixels[0][x])
        samples.append(image.pixels[image.height - 1][x])
    for y in range(image.height):
        samples.append(image.pixels[y][0])
        samples.append(image.pixels[y][image.width - 1])
    return RgbPixel(
        red=median_channel([pixel.red for pixel in samples]),
        green=median_channel([pixel.green for pixel in samples]),
        blue=median_channel([pixel.blue for pixel in samples]),
    )


def median_channel(values: list[int]) -> int:
    sorted_values = sorted(values)
    return sorted_values[len(sorted_values) // 2]


def color_distance(pixel: RgbPixel, background: RgbPixel) -> int:
    return (
        abs(pixel.red - background.red)
        + abs(pixel.green - background.green)
        + abs(pixel.blue - background.blue)
    )


def detect_pixel_clusters(
    image: DecodedPngImage,
    bounds: ChartImageBounds,
    foreground_mask: list[list[bool]],
) -> list[PixelCluster]:
    active_columns = [
        x
        for x in range(bounds.left, bounds.right + 1)
        if sum(1 for y in range(bounds.top, bounds.bottom + 1) if foreground_mask[y][x]) >= 2
    ]
    groups = group_active_columns(active_columns)
    clusters: list[PixelCluster] = []
    for left, right in groups:
        cluster = build_pixel_cluster(image, foreground_mask, bounds, left, right)
        if cluster is not None:
            clusters.append(cluster)
    return clusters


def group_active_columns(active_columns: list[int]) -> list[tuple[int, int]]:
    if not active_columns:
        return []
    groups: list[tuple[int, int]] = []
    group_left = active_columns[0]
    previous = active_columns[0]
    for column in active_columns[1:]:
        if column - previous > 3:
            groups.append((group_left, previous))
            group_left = column
        previous = column
    groups.append((group_left, previous))
    return [(left, right) for left, right in groups if right - left + 1 >= 2]


def build_pixel_cluster(
    image: DecodedPngImage,
    foreground_mask: list[list[bool]],
    bounds: ChartImageBounds,
    left: int,
    right: int,
) -> PixelCluster | None:
    active_points = [
        (x, y)
        for y in range(bounds.top, bounds.bottom + 1)
        for x in range(left, right + 1)
        if foreground_mask[y][x]
    ]
    if len(active_points) < 4:
        return None
    high_y = min(y for _, y in active_points)
    low_y = max(y for _, y in active_points)
    width = right - left + 1
    body_rows = [
        y
        for y in range(high_y, low_y + 1)
        if sum(1 for x in range(left, right + 1) if foreground_mask[y][x])
        >= max(2, width // 2)
    ]
    if body_rows:
        body_top_y = min(body_rows)
        body_bottom_y = max(body_rows)
    else:
        body_top_y = high_y
        body_bottom_y = low_y
    direction = detect_cluster_direction(image, foreground_mask, left, right, high_y, low_y)
    return PixelCluster(
        left=left,
        right=right,
        high_y=high_y,
        low_y=low_y,
        body_top_y=body_top_y,
        body_bottom_y=body_bottom_y,
        direction=direction,
    )


def detect_cluster_direction(
    image: DecodedPngImage,
    foreground_mask: list[list[bool]],
    left: int,
    right: int,
    high_y: int,
    low_y: int,
) -> ChartTrendDirection:
    red_score = 0
    green_score = 0
    for y in range(high_y, low_y + 1):
        for x in range(left, right + 1):
            if not foreground_mask[y][x]:
                continue
            pixel = image.pixels[y][x]
            if pixel.green > pixel.red + 20:
                green_score += 1
            elif pixel.red > pixel.green + 20:
                red_score += 1
    if green_score > red_score:
        return ChartTrendDirection.BULLISH
    if red_score > green_score:
        return ChartTrendDirection.BEARISH
    return ChartTrendDirection.UNKNOWN


def clusters_to_candles(
    clusters: list[PixelCluster],
    bounds: ChartImageBounds,
    config: ChartImageExtractionConfig,
) -> list[ChartScreenshotCandle]:
    sorted_clusters = sorted(clusters, key=lambda cluster: (cluster.left + cluster.right) / 2)
    duration = timeframe_duration(config.timeframe)
    candles: list[ChartScreenshotCandle] = []
    for index, cluster in enumerate(sorted_clusters):
        high = pixel_y_to_price(cluster.high_y, bounds, config)
        low = pixel_y_to_price(cluster.low_y, bounds, config)
        body_top = pixel_y_to_price(cluster.body_top_y, bounds, config)
        body_bottom = pixel_y_to_price(cluster.body_bottom_y, bounds, config)
        if cluster.direction == ChartTrendDirection.BEARISH:
            open_price = body_top
            close_price = body_bottom
        else:
            open_price = body_bottom
            close_price = body_top
        candles.append(
            ChartScreenshotCandle(
                timestamp=config.window_start + (duration * index),
                open=open_price,
                high=max(high, open_price, close_price),
                low=min(low, open_price, close_price),
                close=close_price,
                volume=None,
            )
        )
    return candles


def pixel_y_to_price(
    y: int,
    bounds: ChartImageBounds,
    config: ChartImageExtractionConfig,
) -> Decimal:
    price_range = config.price_max - config.price_min
    pixel_range = Decimal(bounds.bottom - bounds.top)
    distance_from_bottom = Decimal(bounds.bottom - y)
    price = config.price_min + ((distance_from_bottom / pixel_range) * price_range)
    return price.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def calculate_image_extraction_confidence(
    clusters: list[PixelCluster],
    bounds: ChartImageBounds,
) -> Decimal:
    chart_width = Decimal(bounds.right - bounds.left + 1)
    cluster_width = sum(cluster.right - cluster.left + 1 for cluster in clusters)
    density = min(Decimal(cluster_width) / chart_width * Decimal("2"), Decimal("1"))
    candle_count_score = min(Decimal(len(clusters)) / Decimal("20"), Decimal("1"))
    confidence = (density * Decimal("0.45")) + (candle_count_score * Decimal("0.55"))
    return confidence.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
