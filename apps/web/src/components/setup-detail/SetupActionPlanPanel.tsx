import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { boundedSectionItems, itemBody, itemTitle, recordSection } from "@/lib/setup-detail/composeSetupDetail";
import { sanitizeSetupText, setupLabel } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupActionPlanPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupActionPlanPanel({ model }: SetupActionPlanPanelProps) {
  const actionPlan = model.actionPlanSection;
  const plan = recordSection(actionPlan?.plan);
  const actionItems = boundedSectionItems(actionPlan?.action_items);

  return (
    <Panel title="Action Plan" eyebrow="Read-only backend follow-up">
      {!actionPlan || actionPlan.missing ? (
        <SetupEmptySection title="Action plan unavailable" message="No persisted backend follow-up plan was returned for this signal." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={String(plan?.status || "Status unavailable")} tone={toneForQuality(String(plan?.status || ""))} />
            <Badge value={`${String(actionPlan.due_count || 0)} due`} tone="info" />
            <Badge value={`${String(actionPlan.completed_count || 0)} completed`} tone="good" />
          </div>
          {plan?.summary && <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(String(plan.summary))}</p>}
          {actionItems.length === 0 ? (
            <SetupEmptySection title="No action items" message="The action plan returned no follow-up items." />
          ) : (
            <div className="space-y-3">
              {actionItems.map((item) => (
                <div key={String(item.id || item.idempotency_key || itemTitle(item))} className="muted-surface rounded-lg p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-[var(--strong)]">{itemTitle(item)}</h3>
                    <Badge value={String(item.status || "unknown")} tone={toneForQuality(String(item.status || ""))} />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(itemBody(item))}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    {setupLabel(String(item.action_type || "backend follow-up"))} | Due {formatDateTime(String(item.due_at || ""))}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
