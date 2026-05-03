import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Badge } from "@/components/status/badge";
import type { ScannerData } from "@/lib/scanner/types";

export function ScannerHeader({ data }: { data: ScannerData }) {
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Scanner controls</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Watchlist scanner</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Configure backend deterministic scans for watchlists and single symbols. This surface starts analysis runs only and does not execute orders or send messages.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Badge value={data.workspace?.name || "No workspace"} tone={data.workspace ? "info" : "warning"} />
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["dashboard", "brief", "triage", "dataOnboarding"]} />
      </div>
    </section>
  );
}
