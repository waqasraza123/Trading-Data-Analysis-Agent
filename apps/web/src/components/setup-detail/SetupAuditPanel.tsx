import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupAuditPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupAuditPanel({ model }: SetupAuditPanelProps) {
  const timeline = model.auditTimeline;

  return (
    <Panel title="Audit Timeline" eyebrow="Traceability">
      {!timeline ? (
        <SetupEmptySection title="Audit timeline unavailable" message="No audit timeline payload was returned for this signal." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={`Completeness ${formatPercent(timeline.completeness_score)}`} tone="info" />
            <Badge value={`${timeline.events.length} events`} tone="neutral" />
          </div>
          <details open>
            <summary className="cursor-pointer text-sm font-semibold text-[var(--strong)]">Recent trace events</summary>
            <div className="mt-3 space-y-3">
              {timeline.events.slice(0, 8).map((event, index) => (
                <AnimatedListItem
                  as="article"
                  key={`timeline-${index}`}
                  style={motionRevealDensityStyle(index, "compact")}
                >
                  <div className="muted-surface rounded-lg p-4">
                    <p className="text-sm font-medium text-[var(--strong)]">{setupRecordText(event)}</p>
                    <p className="mt-2 text-xs text-slate-500">{formatDateTime(String(event.occurred_at || event.created_at || ""))}</p>
                  </div>
                </AnimatedListItem>
              ))}
            </div>
          </details>
          {timeline.missing_sections.length > 0 && (
            <p className="text-xs text-slate-500">Missing sections: {timeline.missing_sections.join(", ")}</p>
          )}
        </div>
      )}
    </Panel>
  );
}
