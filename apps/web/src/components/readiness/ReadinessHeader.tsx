import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Badge } from "@/components/status/badge";
import type { ProductReadinessPageData } from "@/lib/readiness/types";
import { readinessLabelTone, readinessLabelText } from "@/lib/readiness/labels";

export function ReadinessHeader({ data }: { data: ProductReadinessPageData }) {
  const label = data.selectedRun?.readiness_label || "unknown";
  return (
    <section className="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-slate-500">Guided setup</p>
        <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Product readiness checklist</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
          Validate whether the product is ready for daily operator review. This page does not run scans, send alerts, execute broker actions, auto-trade, or provide financial advice.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Badge value={data.workspace?.name || "No workspace"} tone={data.workspace ? "info" : "warning"} />
        <Badge value={readinessLabelText(label)} tone={readinessLabelTone(label)} />
        <WorkflowLinks
          workspaceId={data.workspace?.id}
          targets={["commandCenter", "dataOnboarding", "scanner", "preferences", "notifications", "journal"]}
        />
      </div>
    </section>
  );
}
