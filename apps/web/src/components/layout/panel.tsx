import type { ReactNode } from "react";
import { MetricCard as UiMetricCard } from "@/components/ui/MetricCard";
import { Section } from "@/components/ui/Section";

type PanelProps = {
  title?: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Panel({ title, eyebrow, action, children, className = "" }: PanelProps) {
  return <Section title={title} eyebrow={eyebrow} action={action} className={className}>{children}</Section>;
}

type MetricCardProps = {
  label: string;
  value: string;
  detail?: string;
};

export function MetricCard({ label, value, detail }: MetricCardProps) {
  return <UiMetricCard label={label} value={value} detail={detail} />;
}
