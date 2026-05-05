import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { remediationHref, remediationLabel } from "@/lib/readiness/labels";
import type { ProductReadinessRun } from "@/lib/readiness/types";

export function ReadinessRemediationPanel({
  run,
  workspaceId,
}: {
  run: ProductReadinessRun;
  workspaceId?: string | null;
}) {
  const checks = [...run.blockers_json, ...run.warnings_json];
  const uniqueChecks = checks.filter(
    (check, index) =>
      checks.findIndex((candidate) => remediationHref(candidate, workspaceId) === remediationHref(check, workspaceId)) === index,
  );
  return (
    <Panel title="Guided remediation" eyebrow="Explicit next steps">
      {uniqueChecks.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm leading-6 text-slate-500">
          No guided remediation is required. Keep using explicit daily workflows when you want to refresh stored intelligence.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {uniqueChecks.map((check) => (
            <Link
              key={`${check.key}-${check.related_route || ""}`}
              className="muted-surface rounded-lg p-4 hover:bg-slate-100 dark:hover:bg-slate-900"
              href={remediationHref(check, workspaceId)}
            >
              <p className="font-semibold text-[var(--strong)]">{remediationLabel(check)}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{check.remediation}</p>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
