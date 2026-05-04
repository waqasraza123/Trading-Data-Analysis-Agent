import { Panel } from "@/components/layout/panel";
import type { JsonRecord } from "@/lib/api/types";
import { setupRecordDetail, setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupZonesPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupZonesPanel({ model }: SetupZonesPanelProps) {
  const setupContext = model.setupContext;

  return (
    <Panel title="Context Zones" eyebrow="Review levels">
      {!setupContext ? (
        <SetupEmptySection title="Context zones unavailable" message="No setup context payload was returned." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <ZoneList title="Observation Zones" items={setupContext.observation_zones_json} empty="No observation zones returned." />
          <ZoneList title="Invalidation Context" items={setupContext.invalidation_context_json} empty="No invalidation context returned." />
          <ZoneList title="Target Context Zones" items={setupContext.target_context_zones_json} empty="No target context zones returned." />
        </div>
      )}
    </Panel>
  );
}

function ZoneList({ title, items, empty }: { title: string; items: JsonRecord[]; empty: string }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      {items.length === 0 ? (
        <SetupEmptySection title={title} message={empty} />
      ) : (
        items.slice(0, 6).map((item, index) => (
          <div key={`${title}-${index}`} className="muted-surface rounded-lg p-4">
            <p className="text-sm font-medium leading-6 text-[var(--strong)]">{setupRecordText(item)}</p>
            {setupRecordDetail(item) && <p className="mt-2 text-xs text-slate-500">{setupRecordDetail(item)}</p>}
          </div>
        ))
      )}
    </div>
  );
}
