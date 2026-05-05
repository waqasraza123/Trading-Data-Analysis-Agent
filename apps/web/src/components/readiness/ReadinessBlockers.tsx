import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { checkStatusTone, remediationHref, remediationLabel } from "@/lib/readiness/labels";
import type { ProductReadinessCheck } from "@/lib/readiness/types";

export function ReadinessBlockers({
  blockers,
  warnings,
  workspaceId,
}: {
  blockers: ProductReadinessCheck[];
  warnings: ProductReadinessCheck[];
  workspaceId?: string | null;
}) {
  const items = [...blockers, ...warnings].slice(0, 8);
  return (
    <Panel title="Blockers and warnings" eyebrow={`${blockers.length} blockers · ${warnings.length} warnings`}>
      {items.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
          No blockers or warnings were reported in the latest readiness run.
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((check) => (
            <div key={check.key} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{check.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{check.summary}</p>
                </div>
                <Badge value={check.status} tone={checkStatusTone(check.status)} />
              </div>
              <Link
                className="mt-3 inline-flex rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium text-[var(--info)] hover:bg-slate-100 dark:hover:bg-slate-800"
                href={remediationHref(check, workspaceId)}
              >
                {remediationLabel(check)}
              </Link>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
