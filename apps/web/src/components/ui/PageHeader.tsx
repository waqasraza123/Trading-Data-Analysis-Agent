import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  meta?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({ eyebrow, title, description, meta, actions, className }: PageHeaderProps) {
  return (
    <section className={cn("relative overflow-hidden rounded-3xl border border-[var(--border)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--surface)_96%,transparent),color-mix(in_srgb,var(--accent-soft)_28%,var(--surface)))] p-5 shadow-panel sm:p-6 lg:p-7", className)}>
      <div className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/70 to-transparent dark:via-white/20" />
      <div className="relative flex flex-wrap items-end justify-between gap-5">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">{eyebrow}</p>
          <h2 className="mt-2 text-3xl font-semibold text-[var(--strong)] sm:text-4xl">{title}</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--text-muted)]">{description}</p>
        </div>
        {actions && <div className="flex max-w-full flex-wrap items-center justify-end gap-3">{actions}</div>}
      </div>
      <div className="relative">
        {meta && <div className="mt-4 flex flex-wrap gap-2">{meta}</div>}
      </div>
    </section>
  );
}
