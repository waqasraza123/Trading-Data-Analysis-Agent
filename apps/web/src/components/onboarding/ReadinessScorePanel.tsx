import { onboardingReadinessLabel, onboardingTone, safeOnboardingCopy } from "@/lib/onboarding/labels";
import { cn } from "@/lib/ui/cn";
import { motionCardClass, motionRevealPresetClass } from "@/lib/ui/motion";
import type { OnboardingStatusResponse } from "@/lib/onboarding/types";

export function ReadinessScorePanel({ status }: { status: OnboardingStatusResponse }) {
  const score = Math.round(status.status.readiness_score * 100);
  return (
    <section
      className={cn(
        "rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5",
        motionCardClass,
        motionRevealPresetClass("scale-subtle"),
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-[var(--strong)]">Readiness score</p>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {safeOnboardingCopy(status.status.summary)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-4xl font-semibold text-[var(--strong)]">{score}%</p>
          <span className={`mt-2 inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${onboardingTone(status.status.readiness_label)}`}>
            {onboardingReadinessLabel(status.status.readiness_label)}
          </span>
        </div>
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-100">
        <div className="h-full rounded-full bg-[var(--accent)]" style={{ width: `${score}%` }} />
      </div>
    </section>
  );
}
