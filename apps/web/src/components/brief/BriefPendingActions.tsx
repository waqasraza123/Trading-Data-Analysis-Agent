import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import { BriefEmptyState } from "./BriefEmptyState";

export function BriefPendingActions({ brief }: { brief: WorkspaceBrief }) {
  return (
    <Panel title="Pending Actions" eyebrow="Backend action items">
      {brief.pendingActions.length === 0 ? (
        <BriefEmptyState
          status={brief.sectionStatuses.pendingActions}
          fallbackTitle="No pending backend actions"
          fallbackMessage="No due backend action items were returned."
        />
      ) : (
        <div className="space-y-3">
          {brief.pendingActions.map((action) => (
            <div key={action.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{action.safeLabel}</h3>
                  <p className="mt-1 text-sm text-slate-500">{humanizeLabel(action.actionType)}</p>
                </div>
                <Badge value={action.status} tone={toneForQuality(action.status)} />
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <Detail label="Source" value={action.source} />
                <Detail label="Due" value={formatDateTime(action.dueTime)} />
              </dl>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}
