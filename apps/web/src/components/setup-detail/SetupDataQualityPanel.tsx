import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupDataQualityPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupDataQualityPanel({ model }: SetupDataQualityPanelProps) {
  const warnings = model.setupContext?.data_quality_warnings_json || [];
  const qualityRun = model.quality?.quality_run || null;

  return (
    <Panel title="Data Quality" eyebrow="Freshness and gate findings">
      {!qualityRun && warnings.length === 0 ? (
        <SetupEmptySection title="No data-quality context" message="No data-quality warnings or quality gate run was returned." />
      ) : (
        <div className="space-y-4">
          {qualityRun && (
            <AnimatedListItem as="article" style={motionRevealDensityStyle(0, "compact")}>
              <div className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={qualityRun.quality_label} tone={toneForQuality(qualityRun.quality_label)} />
                  <Badge value={qualityRun.status} tone={toneForQuality(qualityRun.status)} />
                  <Badge value={formatPercent(qualityRun.quality_score)} tone="info" />
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{qualityRun.summary}</p>
                <p className="mt-2 text-xs text-slate-500">Checked {formatDateTime(qualityRun.checked_at)}</p>
              </div>
            </AnimatedListItem>
          )}
          {warnings.map((warning, index) => (
            <AnimatedListItem
              as="article"
              key={`data-quality-warning-${index}`}
              style={motionRevealDensityStyle(qualityRun ? index + 1 : index, "compact")}
            >
              <div className="muted-surface rounded-lg p-4 text-sm">{setupRecordText(warning)}</div>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}
