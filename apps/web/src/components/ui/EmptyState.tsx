import type { ReactNode } from "react";
import { ButtonLink } from "./Button";
import { MutedCard } from "./Card";

type EmptyStateProps = {
  title: string;
  message: string;
  action?: ReactNode;
  href?: string;
  actionLabel?: string;
};

export function EmptyState({ title, message, action, href, actionLabel = "Open" }: EmptyStateProps) {
  return (
    <MutedCard className="p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--text-muted)]">{message}</p>
        </div>
        {action || (href ? <ButtonLink href={href}>{actionLabel}</ButtonLink> : null)}
      </div>
    </MutedCard>
  );
}
