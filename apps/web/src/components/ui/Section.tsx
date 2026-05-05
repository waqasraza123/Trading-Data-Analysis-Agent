import type { ReactNode } from "react";
import { Card } from "./Card";

type SectionProps = {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Section({ title, eyebrow, action, children, className = "" }: SectionProps) {
  return (
    <Card className={className}>
      {(title || eyebrow || action) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {eyebrow && <p className="text-xs font-semibold uppercase text-slate-500">{eyebrow}</p>}
            {title && <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      {children}
    </Card>
  );
}
