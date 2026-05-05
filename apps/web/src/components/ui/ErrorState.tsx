import type { ReactNode } from "react";
import { Badge } from "./Badge";
import { Section } from "./Section";

type ErrorStateProps = {
  title: string;
  message?: string;
  status?: string | number | null;
  action?: ReactNode;
};

export function ErrorState({ title, message, status, action }: ErrorStateProps) {
  return (
    <Section
      eyebrow="API status"
      title={title}
      action={status ? <Badge value={String(status)} tone="warning" /> : action}
    >
      {message && <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{message}</p>}
      {status && action && <div className="mt-4">{action}</div>}
    </Section>
  );
}
