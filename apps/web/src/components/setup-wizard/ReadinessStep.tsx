"use client";

import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function ReadinessStep({ mutation, onComplete, onSkip }: SetupWizardStepProps) {
  return (
    <Panel title="Readiness check" eyebrow="Explicit validation">
      <div className="space-y-4">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          The readiness check reads current setup state and saves an auditable checklist run. It does not seed data, run workflows, fetch providers, send notifications, execute broker actions, auto-trade, or produce financial advice.
        </p>
        <div className="flex flex-wrap gap-3">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="button" onClick={() => onComplete("readiness_check", { run: true })}>
            Run readiness check
          </button>
          <button className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" type="button" onClick={() => onSkip("readiness_check")}>
            Skip readiness
          </button>
        </div>
      </div>
    </Panel>
  );
}
