import type { CandleRead } from "@/lib/data-onboarding/types";
import type { ChartCandle, ChartCandleSlot } from "./types";

const timeframeMultipliers: Record<string, number> = {
  m: 60_000,
  h: 3_600_000,
  d: 86_400_000,
  w: 604_800_000,
};

export function normalizeChartCandles(candles: CandleRead[]): ChartCandle[] {
  return candles
    .map((candle) => {
      const open = numberValue(candle.open);
      const high = numberValue(candle.high);
      const low = numberValue(candle.low);
      const close = numberValue(candle.close);
      if (![open, high, low, close].every((value) => Number.isFinite(value)) || high < low) {
        return null;
      }
      return {
        id: candle.id,
        timestamp: candle.timestamp,
        open,
        high,
        low,
        close,
        volume: nullableNumber(candle.volume),
        isFinal: candle.is_final,
        qualityScore: nullableNumber(candle.quality_score),
      } satisfies ChartCandle;
    })
    .filter((candle): candle is ChartCandle => candle !== null)
    .sort((left, right) => timestampMs(left.timestamp) - timestampMs(right.timestamp));
}

export function buildCandleSlots(
  candles: ChartCandle[],
  timeframe: string,
  maxSlots = 240,
): ChartCandleSlot[] {
  const intervalMs = timeframeToMilliseconds(timeframe);
  const sortedCandles = candles
    .filter((candle) => Number.isFinite(timestampMs(candle.timestamp)))
    .sort((left, right) => timestampMs(left.timestamp) - timestampMs(right.timestamp));
  const slots: ChartCandleSlot[] = [];
  sortedCandles.forEach((candle, candleIndex) => {
    const previous = sortedCandles[candleIndex - 1];
    if (previous && intervalMs) {
      const missingCount = Math.max(
        0,
        Math.round((timestampMs(candle.timestamp) - timestampMs(previous.timestamp)) / intervalMs) - 1,
      );
      if (missingCount > 0) {
        const availableGapSlots = Math.max(1, maxSlots - sortedCandles.length - slots.length);
        const gapSlots = Math.min(missingCount, availableGapSlots);
        for (let gapIndex = 0; gapIndex < gapSlots; gapIndex += 1) {
          slots.push({
            kind: "gap",
            index: slots.length,
            timestamp: new Date(timestampMs(previous.timestamp) + intervalMs * (gapIndex + 1)).toISOString(),
            missingCount: gapIndex === gapSlots - 1 ? missingCount - gapSlots + 1 : 1,
          });
        }
      }
    }
    slots.push({
      kind: "candle",
      index: slots.length,
      timestamp: candle.timestamp,
      candle,
    });
  });
  return slots.slice(-maxSlots).map((slot, index) => ({ ...slot, index }));
}

export function timeframeToMilliseconds(timeframe: string): number | null {
  const normalized = timeframe.trim().toLowerCase();
  const match = normalized.match(/^(\d+)([mhdw])$/);
  if (!match) {
    return null;
  }
  const amount = Number(match[1]);
  const multiplier = timeframeMultipliers[match[2]];
  if (!Number.isFinite(amount) || !multiplier) {
    return null;
  }
  return amount * multiplier;
}

export function expandWindowAroundSignal(
  start: string | null | undefined,
  end: string | null | undefined,
  timeframe: string,
  desiredCandles = 120,
): { startTime: string; endTime: string } | null {
  const endMs = timestampMs(end || "");
  const startMs = timestampMs(start || "");
  const intervalMs = timeframeToMilliseconds(timeframe) || 60_000;
  if (!Number.isFinite(endMs) && !Number.isFinite(startMs)) {
    return null;
  }
  const anchorEnd = Number.isFinite(endMs) ? endMs : startMs;
  const anchorStart = Number.isFinite(startMs)
    ? Math.min(startMs, anchorEnd - intervalMs * Math.floor(desiredCandles * 0.7))
    : anchorEnd - intervalMs * desiredCandles;
  const paddedStart = anchorStart - intervalMs * Math.floor(desiredCandles * 0.25);
  const paddedEnd = anchorEnd + intervalMs * Math.floor(desiredCandles * 0.25);
  return {
    startTime: new Date(paddedStart).toISOString(),
    endTime: new Date(paddedEnd).toISOString(),
  };
}

export function latestFinalCandle(candles: ChartCandle[]): ChartCandle | null {
  const finalCandles = candles.filter((candle) => candle.isFinal);
  return finalCandles[finalCandles.length - 1] || null;
}

export function timestampMs(value: string): number {
  const date = new Date(value);
  return date.getTime();
}

function numberValue(value: string | number | null | undefined): number {
  return Number(value);
}

function nullableNumber(value: string | number | null | undefined): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
