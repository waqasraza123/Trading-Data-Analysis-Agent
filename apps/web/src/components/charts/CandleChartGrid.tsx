import { ticksForDomain } from "@/lib/charts/scales";
import type { ChartScales } from "@/lib/charts/types";

export function CandleChartGrid({ scales }: { scales: ChartScales }) {
  const ticks = ticksForDomain(scales.domain, 5);
  const left = scales.padding.left;
  const right = scales.width - scales.padding.right;
  return (
    <g aria-hidden="true">
      {ticks.map((tick) => {
        const y = scales.yForPrice(tick);
        return (
          <line
            key={tick}
            x1={left}
            x2={right}
            y1={y}
            y2={y}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-800"
            strokeWidth={1}
          />
        );
      })}
    </g>
  );
}
