import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupHistoricalCasesPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupHistoricalCasesPanel({ model }: SetupHistoricalCasesPanelProps) {
  const cases = model.historicalCases?.results || [];

  return (
    <Panel title="Historical Similar Cases" eyebrow="Deterministic similarity">
      {cases.length === 0 ? (
        <SetupEmptySection title="No similar cases" message="Historical case search did not return comparable stored setups." />
      ) : (
        <div className="space-y-3">
          {cases.map((item, index) => (
            <AnimatedListItem as="article" key={item.matched_signal_id} style={motionRevealDensityStyle(index, "compact")}>
              <div className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  <Badge value={item.signal_summary.bias} tone={toneForBias(item.signal_summary.bias)} />
                  <Badge value={item.signal_summary.confidence_label} tone={toneForQuality(item.signal_summary.confidence_label)} />
                  <Badge value={item.signal_summary.pattern_type || "No pattern"} tone="info" />
                </div>
                <span className="text-sm font-medium text-slate-500">Similarity {formatPercent(item.similarity_score)}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--strong)]">
                {sanitizeSetupText(item.signal_summary.summary || item.deterministic_explanation_summary || "Stored case summary unavailable.")}
              </p>
              {item.matched_reasons.length > 0 && (
                <p className="mt-2 text-xs text-slate-500">
                  Similarity reasons: {item.matched_reasons.map(setupLabel).join(", ")}
                </p>
              )}
              {item.outcome_summary && (
                <p className="mt-2 text-xs text-slate-500">
                  Outcome summary: {Object.keys(item.outcome_summary).slice(0, 5).map(setupLabel).join(", ")}
                </p>
              )}
              </div>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}
