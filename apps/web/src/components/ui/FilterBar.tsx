import type { ReactNode } from "react";
import { Section } from "./Section";

type FilterBarProps = {
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
};

export function FilterBar({ title = "Filters", children, actions }: FilterBarProps) {
  return (
    <Section title={title} eyebrow="Scope" action={actions} className="p-4 sm:p-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{children}</div>
    </Section>
  );
}
