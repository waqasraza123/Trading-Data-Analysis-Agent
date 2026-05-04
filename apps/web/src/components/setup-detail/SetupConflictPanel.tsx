import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { setupLabel, setupRecordText, sanitizeSetupText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupConflictPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupConflictPanel({ model }: SetupConflictPanelProps) {
  const riskNotes = model.riskNotes;
  const qualityFindings = model.quality?.findings || [];
  const readinessWarnings = model.readiness?.warnings || [];
  const crossAssetResults = model.crossAssetResults.filter((result) =>
    ["divergent", "conflicting", "inverse"].includes(result.alignment_label),
  );
  const hasContent =
    riskNotes.length > 0 ||
    qualityFindings.length > 0 ||
    readinessWarnings.length > 0 ||
    crossAssetResults.length > 0 ||
    Boolean(model.multiTimeframeContext?.warnings_json.length);

  return (
    <Panel title="Risk And Conflict" eyebrow="Review blockers">
      {!hasContent ? (
        <SetupEmptySection title="No conflict context" message="No risk notes, quality findings, or context conflicts were returned." />
      ) : (
        <div className="space-y-4">
          {riskNotes.map((note) => (
            <div key={note.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap gap-2">
                <Badge value={note.severity} tone={toneForQuality(note.severity)} />
                <Badge value={note.code} />
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{sanitizeSetupText(note.message)}</p>
            </div>
          ))}
          {qualityFindings.map((finding) => (
            <div key={finding.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap gap-2">
                <Badge value={finding.severity} tone={toneForQuality(finding.severity)} />
                <Badge value={finding.finding_type} />
              </div>
              <p className="mt-3 text-sm font-semibold text-[var(--strong)]">{finding.title}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(finding.message)}</p>
            </div>
          ))}
          {readinessWarnings.map((warning, index) => (
            <div key={`readiness-warning-${index}`} className="muted-surface rounded-lg p-4 text-sm">
              {setupRecordText(warning)}
            </div>
          ))}
          {model.multiTimeframeContext?.warnings_json.map((warning, index) => (
            <div key={`timeframe-warning-${index}`} className="muted-surface rounded-lg p-4 text-sm">
              <span className="font-semibold text-[var(--strong)]">Timeframe context: </span>
              {setupRecordText(warning)}
            </div>
          ))}
          {crossAssetResults.map((result) => (
            <div key={result.id} className="muted-surface rounded-lg p-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge value={result.alignment_label} tone="warning" />
                <Badge value={result.lead_lag_label} tone="info" />
                <Badge value={result.data_quality_label} tone={toneForQuality(result.data_quality_label)} />
              </div>
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                Cross-asset context for {setupLabel(result.compared_symbol_id)} returned {setupLabel(result.alignment_label)}.
              </p>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
