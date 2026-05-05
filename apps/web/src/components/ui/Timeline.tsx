import type { ReactNode } from "react";

type TimelineItem = {
  id: string;
  title: string;
  time?: string;
  detail?: ReactNode;
};

export function Timeline({ items }: { items: TimelineItem[] }) {
  return (
    <ol className="space-y-3">
      {items.map((item) => (
        <li key={item.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[var(--strong)]">{item.title}</h3>
            {item.time && <span className="text-xs text-slate-500">{item.time}</span>}
          </div>
          {item.detail && <div className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</div>}
        </li>
      ))}
    </ol>
  );
}
