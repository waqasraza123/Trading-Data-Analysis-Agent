import { Badge, toneForQuality } from "@/components/status/badge";
import { OutcomeLabelBadge } from "@/components/status/OutcomeLabelBadge";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupHistoricalReviewPanel({ model }: { model: SetupReviewModel }) {
  const cases = model.historicalCases?.results || [];

  return (
    <SetupReviewSection eyebrow="Historical context" title="Similar cases and observed outcomes">
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-3">
          <p className="text-sm font-semibold text-[var(--strong)]">Similar cases</p>
          {cases.length === 0 ? (
            <SetupReviewEmpty title="No similar cases" message="Historical case search did not return comparable stored setups." />
          ) : (
            cases.map((item, index) => (
              <AnimatedListItem as="article" key={item.matched_signal_id} style={motionRevealDensityStyle(index, "compact")}>
                <SetupReviewCard>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge value={item.signal_summary.bias} tone="info" />
                      <Badge value={item.signal_summary.confidence_label} tone={toneForQuality(item.signal_summary.confidence_label)} />
                      <Badge value={item.signal_summary.pattern_type || "No pattern"} tone="neutral" />
                    </div>
                    <span className="text-sm font-medium text-slate-500">Similarity {formatPercent(item.similarity_score)}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {sanitizeSetupText(item.signal_summary.summary || item.deterministic_explanation_summary || "Stored case summary unavailable.")}
                  </p>
                  {item.outcome_summary && (
                    <p className="mt-2 text-xs text-slate-500">
                      Behavior context: {Object.keys(item.outcome_summary).slice(0, 5).map(setupLabel).join(", ")}
                    </p>
                  )}
                </SetupReviewCard>
              </AnimatedListItem>
            ))
          )}
        </div>
        <div className="space-y-3">
          <p className="text-sm font-semibold text-[var(--strong)]">Recent outcomes by horizon</p>
          {model.outcomes.length === 0 ? (
            <SetupReviewEmpty title="No recent outcomes" message="Outcome evaluation has not returned rows for this setup." />
          ) : (
            model.outcomes.map((outcome, index) => (
              <AnimatedListItem as="article" key={outcome.id} style={motionRevealDensityStyle(index, "compact")}>
                <SetupReviewCard>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge value={`${outcome.horizon_minutes}m horizon`} tone="info" />
                      <Badge value={outcome.evaluation_status} tone={toneForQuality(outcome.evaluation_status)} />
                      <OutcomeLabelBadge value={outcome.outcome_label} />
                    </div>
                    <span className="text-xs text-slate-500">{formatDateTime(outcome.future_window_end)}</span>
                  </div>
                  <p className="mt-3 text-sm text-slate-500">
                    Observed follow-through: {outcome.direction_followed === null ? "Not available" : outcome.direction_followed ? "Yes" : "No"}.
                    Observed reversal: {outcome.reversal_detected ? "Yes" : "No"}.
                  </p>
                </SetupReviewCard>
              </AnimatedListItem>
            ))
          )}
        </div>
      </div>
    </SetupReviewSection>
  );
}
