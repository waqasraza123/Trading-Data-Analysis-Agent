import type { ReactNode } from "react";

type PanelProps = {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Panel({ title, eyebrow, action, children, className = "" }: PanelProps) {
  return (
    <section className={`surface rounded-lg p-5 ${className}`}>
      {(title || eyebrow || action) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {eyebrow && <p className="text-xs font-semibold uppercase text-slate-500">{eyebrow}</p>}
            {title && <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
};

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{value}</p>
      {detail && <p className="mt-1 text-sm text-slate-500">{detail}</p>}
    </div>
  );
}
