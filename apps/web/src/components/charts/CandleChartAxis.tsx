import { ticksForDomain } from "@/lib/charts/scales";
import type { ChartCandleSlot, ChartScales } from "@/lib/charts/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatDecimal } from "@/lib/formatting/numbers";

export function CandleChartAxis({ scales, slots }: { scales: ChartScales; slots: ChartCandleSlot[] }) {
  const priceTicks = ticksForDomain(scales.domain, 5);
  const firstTimestamp = slots[0]?.timestamp || null;
  const lastTimestamp = slots[slots.length - 1]?.timestamp || null;
  const bottom = scales.height - scales.padding.bottom;
  const right = scales.width - scales.padding.right;

  return (
    <g className="text-[10px] fill-slate-500">
      {priceTicks.map((tick) => (
        <text key={tick} x={right + 8} y={scales.yForPrice(tick) + 4}>
          {formatDecimal(tick)}
        </text>
      ))}
      {firstTimestamp && (
        <text x={scales.padding.left} y={bottom + 24} textAnchor="start">
          {formatDateTime(firstTimestamp)}
        </text>
      )}
      {lastTimestamp && (
        <text x={right} y={bottom + 24} textAnchor="end">
          {formatDateTime(lastTimestamp)}
        </text>
      )}
    </g>
  );
}
