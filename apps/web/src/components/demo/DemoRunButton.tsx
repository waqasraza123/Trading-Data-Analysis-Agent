"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { runDemoModeFullFlow } from "@/lib/api/demoMode";
import type { DemoModeRunFullFlow } from "@/lib/demo-mode/types";
import { DemoFlowSteps } from "./DemoFlowSteps";
import { DemoResultLinks } from "./DemoResultLinks";

export function DemoRunButton({ enabled }: { enabled: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [result, setResult] = useState<DemoModeRunFullFlow | null>(null);

  async function runFlow() {
    setPending(true);
    setMessage(null);
    const response = await runDemoModeFullFlow();
    setPending(false);
    if (!response.ok) {
      setMessage(response.error.message);
      return;
    }
    setResult(response.data);
    setMessage(response.data.message);
    router.refresh();
  }

  return (
    <Panel
      title="Run product smoke flow"
      eyebrow="Synthetic data only"
      action={
        <button
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!enabled || pending}
          type="button"
          onClick={runFlow}
        >
          {pending ? "Running demo flow" : "Run demo flow"}
        </button>
      }
    >
      <div className="space-y-4">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          The flow creates deterministic market-intelligence artifacts for local or staging validation. It does not use production market data, external providers, broker connections, auto-trading, or advice language.
        </p>
        {message && <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-100">{message}</p>}
        {result && (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-4">
              {([
                ["Signals", result.signal_ids.length],
                ["Setup contexts", result.setup_context_ids.length],
                ["Priority scores", result.priority_score_ids.length],
                ["Outcomes", result.outcome_ids.length],
              ] as [string, number][]).map(([label, value], index) => (
                <AnimatedListItem
                  as="article"
                  key={label}
                  className={cn(
                    "muted-surface rounded-lg p-4",
                    motionCardClass,
                    motionRevealPresetClass("scale-subtle"),
                  )}
                  style={motionRevealDensityStyle(index, "compact")}
                >
                  <DemoMetric label={label} value={value} />
                </AnimatedListItem>
              ))}
            </div>
            <DemoFlowSteps steps={result.steps} />
            <DemoResultLinks links={result.links} />
          </div>
        )}
      </div>
    </Panel>
  );
}

function DemoMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
