import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { checkStatusTone, remediationHref, remediationLabel } from "@/lib/readiness/labels";
import type { ProductReadinessRun } from "@/lib/readiness/types";

export function ReadinessChecklist({
  run,
  workspaceId,
}: {
  run: ProductReadinessRun;
  workspaceId?: string | null;
}) {
  return (
    <Panel title="Checklist" eyebrow={`${run.checks_json.length} checks`}>
      <div className="grid gap-3">
        {run.checks_json.map((check) => (
          <div key={check.key} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-semibold text-[var(--strong)]">{check.title}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{check.summary}</p>
              </div>
              <Badge value={check.status} tone={checkStatusTone(check.status)} />
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] pt-3">
              <p className="text-sm text-slate-500">{check.remediation}</p>
              <Link
                className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800"
                href={remediationHref(check, workspaceId)}
              >
                {remediationLabel(check)}
              </Link>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}
