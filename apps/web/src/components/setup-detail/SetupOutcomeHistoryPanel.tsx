import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { setupLabel } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupOutcomeHistoryPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupOutcomeHistoryPanel({ model }: SetupOutcomeHistoryPanelProps) {
  return (
    <Panel title="Outcome History" eyebrow="Observed horizons">
      {model.outcomes.length === 0 ? (
        <SetupEmptySection title="No outcome history" message="Outcome evaluation has not returned rows for this signal." />
      ) : (
        <div className="overflow-hidden rounded-lg border border-[var(--line)]">
          <div className="grid grid-cols-4 bg-[var(--panel-muted)] px-4 py-3 text-xs font-semibold uppercase text-slate-500">
            <span>Horizon</span>
            <span>Status</span>
            <span>Observation</span>
            <span>Window end</span>
          </div>
          {model.outcomes.map((outcome, index) => (
            <AnimatedListItem
              as="div"
              key={outcome.id}
              style={motionRevealDensityStyle(index, "compact")}
              className="grid grid-cols-4 gap-3 border-t border-[var(--line)] px-4 py-3 text-sm"
            >
              <span className="font-medium">{outcome.horizon_minutes}m</span>
              <Badge value={outcome.evaluation_status} tone={toneForQuality(outcome.evaluation_status)} />
              <Badge value={setupLabel(outcome.outcome_label)} tone={toneForQuality(outcome.outcome_label)} />
              <span className="text-slate-500">{formatDateTime(outcome.future_window_end)}</span>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}
