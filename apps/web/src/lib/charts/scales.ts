import type {
  ChartCandleSlot,
  ChartDimensions,
  ChartPriceDomain,
  ChartScales,
  ChartZone,
} from "./types";

export const defaultChartDimensions: ChartDimensions = {
  width: 920,
  height: 360,
  padding: {
    top: 24,
    right: 70,
    bottom: 42,
    left: 54,
  },
};

export function createChartScales(
  slots: ChartCandleSlot[],
  zones: ChartZone[],
  dimensions: ChartDimensions = defaultChartDimensions,
): ChartScales {
  const domain = chartPriceDomain(slots, zones);
  const plotWidth = Math.max(1, dimensions.width - dimensions.padding.left - dimensions.padding.right);
  const plotHeight = Math.max(1, dimensions.height - dimensions.padding.top - dimensions.padding.bottom);
  const slotCount = Math.max(1, slots.length);
  const slotWidth = plotWidth / slotCount;
  const candleWidth = Math.max(3, Math.min(12, slotWidth * 0.58));

  return {
    width: dimensions.width,
    height: dimensions.height,
    padding: dimensions.padding,
    plotWidth,
    plotHeight,
    domain,
    candleWidth,
    xForIndex: (index) => dimensions.padding.left + slotWidth * index + slotWidth / 2,
    yForPrice: (price) => {
      const ratio = (price - domain.min) / Math.max(0.0000001, domain.max - domain.min);
      return dimensions.padding.top + plotHeight - ratio * plotHeight;
    },
  };
}

export function chartPriceDomain(slots: ChartCandleSlot[], zones: ChartZone[]): ChartPriceDomain {
  const candlePrices = slots.flatMap((slot) =>
    slot.kind === "candle" ? [slot.candle.low, slot.candle.high] : [],
  );
  const zonePrices = zones.flatMap((zone) =>
    [zone.lower, zone.upper, zone.level].filter((value): value is number => Number.isFinite(value)),
  );
  const prices = [...candlePrices, ...zonePrices].filter((value) => Number.isFinite(value));
  if (prices.length === 0) {
    return { min: 0, max: 1 };
  }
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  if (min === max) {
    const fallbackPadding = Math.max(Math.abs(min) * 0.01, 0.0001);
    return { min: min - fallbackPadding, max: max + fallbackPadding };
  }
  const padding = (max - min) * 0.08;
  return { min: min - padding, max: max + padding };
}

export function ticksForDomain(domain: ChartPriceDomain, count = 5): number[] {
  if (count < 2) {
    return [domain.min, domain.max];
  }
  const step = (domain.max - domain.min) / (count - 1);
  return Array.from({ length: count }, (_, index) => domain.min + step * index);
}

export function slotIndexForTimestamp(slots: ChartCandleSlot[], timestamp: string | null): number | null {
  if (!timestamp || slots.length === 0) {
    return null;
  }
  const target = new Date(timestamp).getTime();
  if (!Number.isFinite(target)) {
    return null;
  }
  let nearestIndex = 0;
  let nearestDistance = Number.POSITIVE_INFINITY;
  slots.forEach((slot, index) => {
    const distance = Math.abs(new Date(slot.timestamp).getTime() - target);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestIndex = index;
    }
  });
  return nearestIndex;
}
