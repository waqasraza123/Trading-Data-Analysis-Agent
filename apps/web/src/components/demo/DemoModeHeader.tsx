import { Badge } from "@/components/status/badge";
import type { DemoModeStatus } from "@/lib/demo-mode/types";

export function DemoModeHeader({ status }: { status: DemoModeStatus | null }) {
  const enabled = Boolean(status?.enabled);
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Demo mode</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Product smoke flow</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Creates a labeled demo workspace, imports deterministic candles, runs analysis, produces review context, scores priority, generates a daily brief, and links the result into the existing dashboard workflow.
        </p>
      </div>
      <Badge value={enabled ? "Enabled" : "Disabled"} tone={enabled ? "good" : "warning"} />
    </section>
  );
}
