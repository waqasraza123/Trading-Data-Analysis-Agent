import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupAuditReviewPanel({ model }: { model: SetupReviewModel }) {
  const timeline = model.auditTimeline;

  return (
    <SetupReviewSection id="audit" eyebrow="Audit" title="Timeline summary and traceability">
      {!timeline ? (
        <SetupReviewEmpty title="Audit timeline unavailable" message="No audit timeline payload was returned for this setup." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={`Completeness ${formatPercent(timeline.completeness_score)}`} tone="info" />
            <Badge value={`${timeline.events.length} events`} tone="neutral" />
            <Badge value={`${timeline.missing_sections.length} missing sections`} tone={timeline.missing_sections.length > 0 ? "warning" : "good"} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {timeline.events.slice(0, 8).map((event, index) => (
              <SetupReviewCard key={`timeline-${index}`}>
                <p className="text-sm font-medium text-[var(--strong)]">{setupRecordText(event)}</p>
                <p className="mt-2 text-xs text-slate-500">{formatDateTime(String(event.occurred_at || event.created_at || ""))}</p>
              </SetupReviewCard>
            ))}
          </div>
          {timeline.warnings.length > 0 && (
            <p className="text-xs leading-5 text-slate-500">Audit warnings: {timeline.warnings.join("; ")}</p>
          )}
        </div>
      )}
    </SetupReviewSection>
  );
}
