import { slotIndexForTimestamp } from "@/lib/charts/scales";
import type {
  ChartCandle,
  ChartCandleSlot,
  ChartPatternMarker,
  ChartScales,
  ChartSignalWindow,
} from "@/lib/charts/types";

export function SignalWindowOverlay({
  scales,
  slots,
  signalWindow,
  patternMarker,
  latestFinalCandle,
}: {
  scales: ChartScales;
  slots: ChartCandleSlot[];
  signalWindow: ChartSignalWindow | null;
  patternMarker: ChartPatternMarker | null;
  latestFinalCandle: ChartCandle | null;
}) {
  const top = scales.padding.top;
  const bottom = scales.height - scales.padding.bottom;
  const windowStartIndex = slotIndexForTimestamp(slots, signalWindow?.start || null);
  const windowEndIndex = slotIndexForTimestamp(slots, signalWindow?.end || null);
  const markerIndex = slotIndexForTimestamp(slots, patternMarker?.timestamp || null);
  const latestIndex = slotIndexForTimestamp(slots, latestFinalCandle?.timestamp || null);

  return (
    <g>
      {signalWindow && windowStartIndex !== null && windowEndIndex !== null && (
        <g>
          <rect
            x={Math.min(scales.xForIndex(windowStartIndex), scales.xForIndex(windowEndIndex))}
            y={top}
            width={Math.max(3, Math.abs(scales.xForIndex(windowEndIndex) - scales.xForIndex(windowStartIndex)))}
            height={scales.plotHeight}
            className="fill-blue-500/10"
          />
          <text
            x={Math.min(scales.xForIndex(windowStartIndex), scales.xForIndex(windowEndIndex)) + 6}
            y={top + 14}
            className="fill-blue-700 text-[10px] dark:fill-blue-200"
          >
            {signalWindow.label}
          </text>
        </g>
      )}
      {markerIndex !== null && patternMarker && (
        <g>
          <line
            x1={scales.xForIndex(markerIndex)}
            x2={scales.xForIndex(markerIndex)}
            y1={top}
            y2={bottom}
            className="stroke-blue-600 dark:stroke-blue-300"
            strokeDasharray="5 5"
          />
          <circle cx={scales.xForIndex(markerIndex)} cy={top + 22} r={4} className="fill-blue-600 dark:fill-blue-300" />
          <text x={scales.xForIndex(markerIndex) + 8} y={top + 25} className="fill-blue-700 text-[10px] dark:fill-blue-200">
            {patternMarker.label}
          </text>
        </g>
      )}
      {latestIndex !== null && latestFinalCandle && (
        <g>
          <line
            x1={scales.xForIndex(latestIndex)}
            x2={scales.xForIndex(latestIndex)}
            y1={top}
            y2={bottom}
            className="stroke-slate-500 dark:stroke-slate-300"
            strokeDasharray="2 4"
          />
          <text x={scales.xForIndex(latestIndex) - 8} y={bottom - 8} textAnchor="end" className="fill-slate-500 text-[10px]">
            Latest final candle
          </text>
        </g>
      )}
    </g>
  );
}
