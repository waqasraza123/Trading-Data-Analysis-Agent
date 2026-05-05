import { Badge } from "@/components/status/badge";
import type { JsonRecord } from "@/lib/api/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { setupRecordDetail, setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupContextReviewPanel({ model }: { model: SetupReviewModel }) {
  const setupContext = model.setupContext;
  const latestFinalCandle = model.setupChart.latestFinalCandle;

  return (
    <SetupReviewSection id="setup-context" eyebrow="Visual setup context" title="Observation, invalidation, and target context">
      {!setupContext ? (
        <SetupReviewEmpty title="Setup context unavailable" message="No setup context payload was returned for this signal." />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <ZoneList title="Observation zones" items={setupContext.observation_zones_json} />
            <ZoneList title="Invalidation context" items={setupContext.invalidation_context_json} />
            <ZoneList title="Target context zones" items={setupContext.target_context_zones_json} />
          </div>
          <SetupReviewCard>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500">Latest final candle</p>
                <p className="mt-1 text-sm font-semibold text-[var(--strong)]">{formatDateTime(latestFinalCandle?.timestamp)}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge value={`${model.setupChart.candles.length} final candles`} tone="info" />
                <Badge value={model.setupChart.status} tone={model.setupChart.status === "ready" ? "good" : "warning"} />
              </div>
            </div>
          </SetupReviewCard>
        </div>
      )}
    </SetupReviewSection>
  );
}

function ZoneList({ title, items }: { title: string; items: JsonRecord[] }) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold text-[var(--strong)]">{title}</p>
      {items.length === 0 ? (
        <SetupReviewEmpty title={title} message="No context rows returned." />
      ) : (
        items.slice(0, 5).map((item, index) => (
          <SetupReviewCard key={`${title}-${index}`}>
            <p className="text-sm leading-6 text-[var(--strong)]">{setupRecordText(item)}</p>
            {setupRecordDetail(item) && <p className="mt-2 text-xs text-slate-500">{setupRecordDetail(item)}</p>}
          </SetupReviewCard>
        ))
      )}
    </div>
  );
}
