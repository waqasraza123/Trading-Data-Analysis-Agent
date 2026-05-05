import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type TimelineItem = {
  id: string;
  title: string;
  time?: string;
  detail?: ReactNode;
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="relative space-y-3">
      {items.map((item) => (
        <li key={item.id} className={cn("rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_1px_0_rgba(15,23,42,0.04)]")}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[var(--strong)]">{item.title}</h3>
            {item.time && <span className="text-xs text-[var(--text-muted)]">{item.time}</span>}
          </div>
          {item.detail && <div className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{item.detail}</div>}
        </li>
      ))}
    </ol>
  );
}
