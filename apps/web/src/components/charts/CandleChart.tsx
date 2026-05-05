import { createChartScales, defaultChartDimensions } from "@/lib/charts/scales";
import type {
  ChartCandle,
  ChartCandleSlot,
  ChartDimensions,
  ChartOverlays,
} from "@/lib/charts/types";
import { CandleChartAxis } from "./CandleChartAxis";
import { CandleChartGrid } from "./CandleChartGrid";
import { CandleSeries } from "./CandleSeries";
import { ChartEmptyState } from "./ChartEmptyState";
import { OutcomeMarkerOverlay } from "./OutcomeMarkerOverlay";
import { SignalWindowOverlay } from "./SignalWindowOverlay";
import { ZoneOverlay } from "./ZoneOverlay";

type CandleChartProps = {
  slots: ChartCandleSlot[];
  overlays: ChartOverlays;
  latestFinalCandle: ChartCandle | null;
  dimensions?: ChartDimensions;
};

export function CandleChart({
  slots,
  overlays,
  latestFinalCandle,
  dimensions = defaultChartDimensions,
}: CandleChartProps) {
  if (slots.length === 0) {
    return (
      <ChartEmptyState
        title="Chart data unavailable"
        message="No final candles were returned for the selected setup window."
      />
    );
  }

  const scales = createChartScales(slots, overlays.zones, dimensions);

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--panel)]">
      <svg
        role="img"
        aria-label="Visual setup chart with final candles and review context overlays"
        viewBox={`0 0 ${dimensions.width} ${dimensions.height}`}
        className="h-auto w-full"
      >
        <rect width={dimensions.width} height={dimensions.height} className="fill-[var(--panel)]" />
        <CandleChartGrid scales={scales} />
        <ZoneOverlay scales={scales} zones={overlays.zones} />
        <SignalWindowOverlay
          scales={scales}
          slots={slots}
          signalWindow={overlays.signalWindow}
          patternMarker={overlays.patternMarker}
          latestFinalCandle={latestFinalCandle}
        />
        <CandleSeries scales={scales} slots={slots} />
        <OutcomeMarkerOverlay scales={scales} slots={slots} markers={overlays.outcomeMarkers} />
        <CandleChartAxis scales={scales} slots={slots} />
      </svg>
    </div>
  );
}
