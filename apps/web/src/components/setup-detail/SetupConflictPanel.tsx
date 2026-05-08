import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { setupLabel, setupRecordText, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupConflictPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupConflictPanel({ model }: SetupConflictPanelProps) {
  const riskNotes = model.riskNotes;
  const qualityFindings = model.quality?.findings || [];
  const readinessWarnings = model.readiness?.warnings || [];
  const timeframeWarnings = model.multiTimeframeContext?.warnings_json || [];
  const crossAssetResults = model.crossAssetResults.filter((result) =>
    ["divergent", "conflicting", "inverse"].includes(result.alignment_label),
  );
  const hasContent =
    riskNotes.length > 0 ||
    qualityFindings.length > 0 ||
    readinessWarnings.length > 0 ||
    crossAssetResults.length > 0 ||
    Boolean(timeframeWarnings.length);
  const indexAfterRiskNotes = riskNotes.length;
  const indexAfterQualityFindings = indexAfterRiskNotes + qualityFindings.length;
  const indexAfterReadinessWarnings = indexAfterQualityFindings + readinessWarnings.length;
  const indexAfterTimeframeWarnings = indexAfterReadinessWarnings + timeframeWarnings.length;

  return (
    <Panel title="Risk And Conflict" eyebrow="Review blockers">
      {!hasContent ? (
        <SetupEmptySection title="No conflict context" message="No risk notes, quality findings, or context conflicts were returned." />
      ) : (
        <div className="space-y-4">
          {riskNotes.map((note, index) => (
            <AnimatedListItem as="article" key={note.id} style={motionRevealDensityStyle(index, "compact")}>
              <div className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={note.severity} tone={toneForQuality(note.severity)} />
                  <Badge value={note.code} />
                </div>
                <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{sanitizeSetupText(note.message)}</p>
              </div>
            </AnimatedListItem>
          ))}
          {qualityFindings.map((finding, index) => (
            <AnimatedListItem as="article" key={finding.id} style={motionRevealDensityStyle(indexAfterRiskNotes + index, "compact")}>
              <div className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={finding.severity} tone={toneForQuality(finding.severity)} />
                  <Badge value={finding.finding_type} />
                </div>
                <p className="mt-3 text-sm font-semibold text-[var(--strong)]">{finding.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(finding.message)}</p>
              </div>
            </AnimatedListItem>
          ))}
          {readinessWarnings.map((warning, index) => (
            <AnimatedListItem as="article" key={`readiness-warning-${index}`} style={motionRevealDensityStyle(indexAfterQualityFindings + index, "compact")}>
              <div className="muted-surface rounded-lg p-4 text-sm">
                {setupRecordText(warning)}
              </div>
            </AnimatedListItem>
          ))}
          {timeframeWarnings.map((warning, index) => (
            <AnimatedListItem as="article" key={`timeframe-warning-${index}`} style={motionRevealDensityStyle(indexAfterReadinessWarnings + index, "compact")}>
              <div className="muted-surface rounded-lg p-4 text-sm">
                <span className="font-semibold text-[var(--strong)]">Timeframe context: </span>
                {setupRecordText(warning)}
              </div>
            </AnimatedListItem>
          ))}
          {crossAssetResults.map((result, index) => (
            <AnimatedListItem as="article" key={result.id} style={motionRevealDensityStyle(indexAfterTimeframeWarnings + index, "compact")}>
              <div className="muted-surface rounded-lg p-4 text-sm">
                <div className="flex flex-wrap gap-2">
                  <Badge value={result.alignment_label} tone="warning" />
                  <Badge value={result.lead_lag_label} tone="info" />
                  <Badge value={result.data_quality_label} tone={toneForQuality(result.data_quality_label)} />
                </div>
                <p className="mt-2 text-slate-600 dark:text-slate-300">
                  Cross-asset context for {setupLabel(result.compared_symbol_id)} returned {setupLabel(result.alignment_label)}.
                </p>
              </div>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}
