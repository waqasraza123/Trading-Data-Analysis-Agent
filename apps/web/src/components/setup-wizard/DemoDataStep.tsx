"use client";

import { FormEvent, useState } from "react";
import { cn } from "@/lib/ui/cn";
import { Panel } from "@/components/layout/panel";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function DemoDataStep({ selectedSymbolIds, selectedTimeframes, selectedSourceId, mutation, onComplete, onSkip }: SetupWizardStepProps) {
  const [enabled, setEnabled] = useState(true);
  const [candleCount, setCandleCount] = useState(160);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!enabled) {
      await onSkip("demo_data");
      return;
    }
    await onComplete("demo_data", {
      enabled,
      symbol_ids: selectedSymbolIds,
      source_id: selectedSourceId || undefined,
      timeframes: selectedTimeframes.length ? selectedTimeframes : ["1m"],
      candle_count: candleCount,
      pattern: "crypto_tick_sample",
    });
  }

  return (
    <AnimatedListItem
      as="section"
      className={cn(motionCardClass, motionRevealPresetClass("scale-subtle"))}
      style={motionRevealDensityStyle(0, "regular")}
    >
      <Panel title="Demo data" eyebrow="Optional synthetic candles">
        <form className="space-y-4" onSubmit={submit}>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            <input checked={enabled} type="checkbox" onChange={(event) => setEnabled(event.target.checked)} />
            Seed deterministic synthetic candles
          </label>
          <label className="block max-w-xs text-sm font-medium text-slate-600 dark:text-slate-300">
            Candle count
            <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" min={40} max={2000} type="number" value={candleCount} onChange={(event) => setCandleCount(Number(event.target.value))} />
          </label>
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            {enabled ? "Seed demo candles" : "Skip demo data"}
          </button>
        </form>
      </Panel>
    </AnimatedListItem>
  );
}
