import { Panel } from "@/components/layout/panel";
import type { JsonRecord } from "@/lib/api/types";
import { setupRecordDetail, setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupWaitAvoidPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupWaitAvoidPanel({ model }: SetupWaitAvoidPanelProps) {
  const setupContext = model.setupContext;

  return (
    <Panel title="Wait, Avoid, Observe" eyebrow="Backend-safe review steps">
      {!setupContext ? (
        <SetupEmptySection title="Review steps unavailable" message="No setup context payload was returned." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <ContextList title="Wait Conditions" items={setupContext.wait_conditions_json} empty="No wait conditions returned." />
          <ContextList title="Avoid Reasons" items={setupContext.avoid_reasons_json} empty="No avoid reasons returned." />
          <ContextList title="Next Observations" items={setupContext.next_observations_json} empty="No next observations returned." />
        </div>
      )}
    </Panel>
  );
}

function ContextList({ title, items, empty }: { title: string; items: JsonRecord[]; empty: string }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      {items.length === 0 ? (
        <SetupEmptySection title={title} message={empty} />
      ) : (
        items.map((item, index) => (
          <div key={`${title}-${index}`} className="muted-surface rounded-lg p-4">
            <p className="text-sm leading-6 text-[var(--strong)]">{setupRecordText(item)}</p>
            {setupRecordDetail(item) && <p className="mt-2 text-xs text-slate-500">{setupRecordDetail(item)}</p>}
          </div>
        ))
      )}
    </div>
  );
}
