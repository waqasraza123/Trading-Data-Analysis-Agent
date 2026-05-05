import type { ChartScales, ChartZone } from "@/lib/charts/types";

const zoneClassName: Record<ChartZone["tone"], string> = {
  neutral: "fill-slate-400/10 stroke-slate-400/50",
  good: "fill-teal-400/10 stroke-teal-500/50",
  warning: "fill-amber-400/12 stroke-amber-500/60",
  danger: "fill-rose-400/10 stroke-rose-500/60",
  info: "fill-blue-400/10 stroke-blue-500/50",
};

export function ZoneOverlay({ scales, zones }: { scales: ChartScales; zones: ChartZone[] }) {
  const left = scales.padding.left;
  const width = scales.plotWidth;
  const right = scales.width - scales.padding.right;
  return (
    <g>
      {zones.slice(0, 14).map((zone) => {
        const y1 = zone.upper !== null ? scales.yForPrice(zone.upper) : zone.level !== null ? scales.yForPrice(zone.level) : null;
        const y2 = zone.lower !== null ? scales.yForPrice(zone.lower) : zone.level !== null ? scales.yForPrice(zone.level) : null;
        if (y1 === null || y2 === null) {
          return null;
        }
        const top = Math.min(y1, y2);
        const height = Math.max(2, Math.abs(y2 - y1));
        return (
          <g key={zone.id}>
            <rect
              x={left}
              y={top}
              width={width}
              height={height}
              className={zoneClassName[zone.tone]}
              strokeDasharray={zone.kind === "supportResistance" ? "4 4" : undefined}
              strokeWidth={1}
            />
            <text x={right - 6} y={top + Math.max(12, Math.min(18, height - 3))} textAnchor="end" className="fill-slate-500 text-[10px]">
              {zone.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
