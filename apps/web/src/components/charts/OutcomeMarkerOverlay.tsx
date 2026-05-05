import { slotIndexForTimestamp } from "@/lib/charts/scales";
import type { ChartCandleSlot, ChartOutcomeMarker, ChartScales } from "@/lib/charts/types";

const markerClassName: Record<ChartOutcomeMarker["kind"], string> = {
  followThrough: "fill-teal-500 stroke-teal-700 dark:fill-teal-300 dark:stroke-teal-100",
  reversal: "fill-rose-500 stroke-rose-700 dark:fill-rose-300 dark:stroke-rose-100",
  noFollowThrough: "fill-amber-500 stroke-amber-700 dark:fill-amber-300 dark:stroke-amber-100",
  insufficient: "fill-slate-400 stroke-slate-600 dark:fill-slate-500 dark:stroke-slate-200",
};

export function OutcomeMarkerOverlay({
  scales,
  slots,
  markers,
}: {
  scales: ChartScales;
  slots: ChartCandleSlot[];
  markers: ChartOutcomeMarker[];
}) {
  return (
    <g>
      {markers.map((marker, markerPosition) => {
        const slotIndex = slotIndexForTimestamp(slots, marker.timestamp);
        if (slotIndex === null) {
          return null;
        }
        const slot = slots[slotIndex];
        const markerPrice = slot.kind === "candle" ? slot.candle.close : (scales.domain.min + scales.domain.max) / 2;
        const x = scales.xForIndex(slotIndex);
        const y = scales.yForPrice(markerPrice) - 10 - (markerPosition % 3) * 12;
        return (
          <g key={marker.id}>
            <circle cx={x} cy={y} r={5} className={markerClassName[marker.kind]} strokeWidth={1.5} />
            <text x={x + 8} y={y + 3} className="fill-slate-600 text-[10px] dark:fill-slate-300">
              {marker.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
