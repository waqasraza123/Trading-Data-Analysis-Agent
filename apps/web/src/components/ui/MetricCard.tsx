import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";

type MetricCardProps = {
  label: string;
  value: string | number;
  detail?: ReactNode;
  trend?: ReactNode;
  className?: string;
  interactive?: boolean;
};

export function MetricCard({ label, value, detail, trend, className, interactive = false }: MetricCardProps) {
  return (
    <div
      className={cn(
        "muted-surface motion-card min-w-0 rounded-2xl p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.42)]",
        interactive && "cursor-pointer",
        interactive && MOTION_INTERACTIVE_CLASS,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="min-w-0 text-xs font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]">{label}</p>
        {trend}
      </div>
      <p className="mt-2 truncate text-2xl font-semibold text-[var(--strong)]">{value}</p>
      {detail && <p className="mt-1 text-sm leading-5 text-[var(--text-muted)]">{detail}</p>}
    </div>
  );
}
