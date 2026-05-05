import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type SectionHeaderProps = {
  title?: string;
  eyebrow?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function SectionHeader({ title, eyebrow, description, action, className }: SectionHeaderProps) {
  if (!title && !eyebrow && !description && !action) {
    return null;
  }
  return (
    <div className={cn("mb-4 flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="min-w-0">
        {eyebrow && <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)]">{eyebrow}</p>}
        {title && <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">{title}</h2>}
        {description && <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">{description}</p>}
      </div>
      {action && <div className="flex flex-wrap items-center justify-end gap-2">{action}</div>}
    </div>
  );
}
