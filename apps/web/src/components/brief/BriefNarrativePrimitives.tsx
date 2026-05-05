import Link from "next/link";
import type { ReactNode } from "react";
import type { StatusTone } from "@/lib/ui/statusStyles";

type BriefPanelProps = {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
};

type BriefBadgeProps = {
  children: ReactNode;
  tone?: StatusTone;
};

const toneClassName: Record<StatusTone, string> = {
  neutral: "border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  good: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  warning: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
  danger: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100",
  info: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-100",
};

export function BriefPanel({ title, eyebrow, children, className = "" }: BriefPanelProps) {
  return (
    <section className={`rounded-3xl border border-white/70 bg-white/86 p-5 shadow-[0_24px_80px_rgba(15,23,42,0.08)] backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 sm:p-6 ${className}`}>
      <div className="mb-5">
        {eyebrow && <p className="text-xs font-semibold uppercase text-slate-500">{eyebrow}</p>}
        <h2 className="mt-1 text-xl font-semibold text-[var(--strong)]">{title}</h2>
      </div>
      {children}
    </section>
  );
}

export function BriefBadge({ children, tone = "neutral" }: BriefBadgeProps) {
  return (
    <span className={`inline-flex max-w-full items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${toneClassName[tone]}`}>
      <span className="truncate">{children}</span>
    </span>
  );
}

export function BriefMetric({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/45">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-[var(--strong)]">{value}</p>
      {detail && <p className="mt-2 text-sm leading-5 text-slate-500">{detail}</p>}
    </div>
  );
}

export function BriefEmptyBlock({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/75 p-5 dark:border-slate-700 dark:bg-slate-900/60">
      <p className="font-semibold text-[var(--strong)]">{title}</p>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{message}</p>
    </div>
  );
}

export function BriefTextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex text-sm font-semibold text-teal-700 hover:text-teal-900 dark:text-teal-300 dark:hover:text-teal-100">
      {children}
    </Link>
  );
}
