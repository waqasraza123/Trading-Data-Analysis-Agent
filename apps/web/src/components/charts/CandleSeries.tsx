import type { ChartCandleSlot, ChartScales } from "@/lib/charts/types";

export function CandleSeries({ scales, slots }: { scales: ChartScales; slots: ChartCandleSlot[] }) {
  return (
    <g>
      {slots.map((slot) => {
        const x = scales.xForIndex(slot.index);
        if (slot.kind === "gap") {
          return (
            <rect
              key={`gap-${slot.index}-${slot.timestamp}`}
              x={x - scales.candleWidth / 2}
              y={scales.padding.top}
              width={Math.max(2, scales.candleWidth)}
              height={scales.plotHeight}
              className="fill-amber-300/20 dark:fill-amber-300/10"
            />
          );
        }
        const candle = slot.candle;
        const openY = scales.yForPrice(candle.open);
        const closeY = scales.yForPrice(candle.close);
        const highY = scales.yForPrice(candle.high);
        const lowY = scales.yForPrice(candle.low);
        const rising = candle.close >= candle.open;
        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.max(2, Math.abs(openY - closeY));
        return (
          <g key={candle.id}>
            <line
              x1={x}
              x2={x}
              y1={highY}
              y2={lowY}
              className={rising ? "stroke-teal-600 dark:stroke-teal-300" : "stroke-rose-600 dark:stroke-rose-300"}
              strokeWidth={1.2}
            />
            <rect
              x={x - scales.candleWidth / 2}
              y={bodyTop}
              width={scales.candleWidth}
              height={bodyHeight}
              rx={1.5}
              className={rising ? "fill-teal-600 dark:fill-teal-300" : "fill-rose-600 dark:fill-rose-300"}
            />
          </g>
        );
      })}
    </g>
  );
}
