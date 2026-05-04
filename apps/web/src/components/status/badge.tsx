import { humanizeLabel } from "@/lib/formatting/labels";

type BadgeTone = "neutral" | "good" | "warning" | "danger" | "info";

type BadgeProps = {
  value: string | null | undefined;
  tone?: BadgeTone;
};

const toneClassName: Record<BadgeTone, string> = {
  neutral: "border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200",
  good: "border-teal-200 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-100",
  warning: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  danger: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
  info: "border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
};

export function Badge({ value, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded-md border px-2.5 py-1 text-xs font-medium ${toneClassName[tone]}`}
    >
      {humanizeLabel(value)}
    </span>
  );
}

export function toneForBias(value: string | null | undefined): BadgeTone {
  const normalized = value?.toLowerCase();
  if (normalized === "bullish") {
    return "good";
  }
  if (normalized === "bearish") {
    return "danger";
  }
  if (normalized === "neutral" || normalized === "no_signal") {
    return "info";
  }
  return "neutral";
}

export function toneForQuality(value: string | null | undefined): BadgeTone {
  const normalized = value?.toLowerCase();
  if (normalized === "strong" || normalized === "fresh" || normalized === "healthy" || normalized === "ready") {
    return "good";
  }
  if (normalized === "acceptable" || normalized === "review_recommended") {
    return "info";
  }
  if (normalized === "weak" || normalized === "stale" || normalized === "degraded") {
    return "warning";
  }
  if (normalized === "unhealthy" || normalized === "failed") {
    return "danger";
  }
  return "neutral";
}
