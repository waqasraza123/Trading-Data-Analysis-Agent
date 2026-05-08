import type { ReactNode } from "react";

import { motionCardClass } from "@/lib/ui/motion";

type SetupReviewSectionProps = {
  id?: string;
  eyebrow: string;
  title: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function SetupReviewSection({ id, eyebrow, title, action, children, className = "" }: SetupReviewSectionProps) {
  return (
    <section id={id} className={`surface ${motionCardClass} rounded-lg p-5 ${className}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">{eyebrow}</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function SetupReviewEmpty({ title, message }: { title: string; message: string }) {
  return (
    <div className={`rounded-lg border border-dashed border-[var(--line)] bg-[var(--panel-muted)] p-4 ${motionCardClass}`}>
      <p className="text-sm font-semibold text-[var(--strong)]">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}

export function SetupReviewCard({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`muted-surface ${motionCardClass} rounded-lg p-4 ${className}`}>{children}</div>;
}
