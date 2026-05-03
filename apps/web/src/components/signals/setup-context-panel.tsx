import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type { JsonRecord, SetupContext } from "@/lib/api/types";
import { humanizeLabel } from "@/lib/formatting/labels";
import { formatPercent } from "@/lib/formatting/numbers";

type SetupContextPanelProps = {
  setupContext: SetupContext | null;
};

export function SetupContextPanel({ setupContext }: SetupContextPanelProps) {
  if (!setupContext) {
    return (
      <EmptyState
        title="Setup context unavailable"
        message="The setup context endpoint did not return data for this signal."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Badge value={setupContext.directional_bias} tone={toneForBias(setupContext.directional_bias)} />
        <Badge value={setupContext.setup_quality_label} tone={toneForQuality(setupContext.setup_quality_label)} />
        <Badge value={formatPercent(setupContext.setup_quality_score)} tone="info" />
        <Badge value={setupContext.status} tone={toneForQuality(setupContext.status)} />
      </div>
      <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
        {setupContext.summary || "No setup context summary returned."}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        <ContextList title="Invalidation context" items={setupContext.invalidation_context_json} />
        <ContextList title="Observation zone" items={setupContext.observation_zones_json} />
        <ContextList title="Wait condition" items={setupContext.wait_conditions_json} />
        <ContextList title="Avoid reason" items={setupContext.avoid_reasons_json} />
      </div>
    </div>
  );
}

function ContextList({ title, items }: { title: string; items: JsonRecord[] }) {
  return (
    <div className="rounded-lg border border-[var(--line)] p-3">
      <h4 className="text-xs font-semibold uppercase text-slate-500">{title}</h4>
      {items.length ? (
        <ul className="mt-3 space-y-2">
          {items.slice(0, 4).map((item, index) => (
            <li key={`${title}-${index}`} className="text-sm leading-6 text-[var(--strong)]">
              {contextText(item)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-500">Not provided.</p>
      )}
    </div>
  );
}

function contextText(item: JsonRecord): string {
  const candidate =
    item.label ||
    item.title ||
    item.message ||
    item.reason ||
    item.condition ||
    item.description ||
    item.context ||
    item.level ||
    "Context item";
  return humanizeLabel(String(candidate));
}
