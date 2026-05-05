import type { JsonRecord } from "@/lib/api/types";
import { setupRecordDetail, setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupWaitAvoidReviewPanel({ model }: { model: SetupReviewModel }) {
  const setupContext = model.setupContext;
  const staleWarnings = setupContext?.data_quality_warnings_json || [];

  return (
    <SetupReviewSection eyebrow="Wait and avoid" title="Unresolved context and data warnings">
      {!setupContext ? (
        <SetupReviewEmpty title="Wait and avoid context unavailable" message="No setup context payload was returned." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-4">
          <ContextList title="Wait conditions" items={setupContext.wait_conditions_json} empty="No wait conditions returned." />
          <ContextList title="Avoid reasons" items={setupContext.avoid_reasons_json} empty="No avoid reasons returned." />
          <ContextList title="Next observations" items={setupContext.next_observations_json} empty="No next observations returned." />
          <ContextList title="Data stale/degraded" items={staleWarnings} empty="No stale or degraded data warnings returned." />
        </div>
      )}
    </SetupReviewSection>
  );
}

function ContextList({ title, items, empty }: { title: string; items: JsonRecord[]; empty: string }) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-[var(--strong)]">{title}</p>
      {items.length === 0 ? (
        <SetupReviewEmpty title={title} message={empty} />
      ) : (
        items.slice(0, 6).map((item, index) => (
          <SetupReviewCard key={`${title}-${index}`}>
            <p className="text-sm leading-6 text-[var(--strong)]">{setupRecordText(item)}</p>
            {setupRecordDetail(item) && <p className="mt-2 text-xs text-slate-500">{setupRecordDetail(item)}</p>}
          </SetupReviewCard>
        ))
      )}
    </div>
  );
}
