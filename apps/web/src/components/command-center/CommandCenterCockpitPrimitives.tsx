import Link from "next/link";
import type { ReactNode } from "react";
import type { CommandCenterTone } from "@/lib/command-center/types";

type CockpitPanelProps = {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
};

type CockpitMetricProps = {
  label: string;
  value: string | number;
  detail?: string;
  tone?: CommandCenterTone;
};

type CockpitBadgeProps = {
  children: ReactNode;
  tone?: CommandCenterTone;
  className?: string;
};

type CockpitActionLinkProps = {
  href: string;
  children: ReactNode;
  tone?: CommandCenterTone;
};

const panelClassName =
  "border border-white/70 bg-white/85 shadow-[0_24px_80px_rgba(15,23,42,0.09)] backdrop-blur dark:border-slate-800/80 dark:bg-slate-950/72 dark:shadow-[0_24px_80px_rgba(0,0,0,0.28)]";

const toneClassName: Record<CommandCenterTone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  good: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  warning: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  danger: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100",
  info: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-100",
};

const metricAccentClassName: Record<CommandCenterTone, string> = {
  neutral: "from-slate-100 to-white dark:from-slate-900 dark:to-slate-950",
  good: "from-emerald-50 to-white dark:from-emerald-950/60 dark:to-slate-950",
  warning: "from-amber-50 to-white dark:from-amber-950/60 dark:to-slate-950",
  danger: "from-rose-50 to-white dark:from-rose-950/60 dark:to-slate-950",
  info: "from-sky-50 to-white dark:from-sky-950/60 dark:to-slate-950",
};

export function CockpitPanel({ title, eyebrow, action, children, className = "" }: CockpitPanelProps) {
  return (
    <section className={`${panelClassName} rounded-3xl p-5 sm:p-6 ${className}`}>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && <p className="text-xs font-semibold uppercase text-slate-500">{eyebrow}</p>}
          <h2 className="mt-1 text-xl font-semibold text-[var(--strong)]">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function CockpitMetric({ label, value, detail, tone = "neutral" }: CockpitMetricProps) {
  return (
    <div className={`min-w-0 rounded-2xl border bg-gradient-to-br p-4 ${toneClassName[tone]} ${metricAccentClassName[tone]}`}>
      <p className="text-xs font-semibold uppercase opacity-75">{label}</p>
      <p className="mt-2 truncate text-3xl font-semibold">{value}</p>
      {detail && <p className="mt-2 text-sm leading-5 opacity-75">{detail}</p>}
    </div>
  );
}

export function CockpitBadge({ children, tone = "neutral", className = "" }: CockpitBadgeProps) {
  return (
    <span className={`inline-flex max-w-full items-center rounded-full border px-2.5 py-1 text-xs font-semibold leading-4 ${toneClassName[tone]} ${className}`}>
      <span className="truncate">{children}</span>
    </span>
  );
}

export function CockpitActionLink({ href, children, tone = "neutral" }: CockpitActionLinkProps) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-10 items-center justify-center rounded-full border px-4 py-2 text-sm font-semibold transition hover:-translate-y-0.5 hover:shadow-sm ${toneClassName[tone]}`}
    >
      {children}
    </Link>
  );
}

export function CockpitEmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/75 p-5 text-sm dark:border-slate-700 dark:bg-slate-900/70">
      <p className="font-semibold text-[var(--strong)]">{title}</p>
      <p className="mt-2 leading-6 text-slate-600 dark:text-slate-300">{message}</p>
    </div>
  );
}
