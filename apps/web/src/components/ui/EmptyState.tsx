import type { ReactNode } from "react";
import { MutedCard } from "./Card";

type EmptyStateProps = {
  title: string;
  message: string;
  action?: ReactNode;
};

export function EmptyState({ title, message, action }: EmptyStateProps) {
  return (
    <MutedCard>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
        </div>
        {action}
      </div>
    </MutedCard>
  );
}
