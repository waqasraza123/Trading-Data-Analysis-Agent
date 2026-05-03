import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { formatPercent } from "@/lib/formatting/numbers";
import { recordSection } from "@/lib/setup-detail/composeSetupDetail";
import { setupLabel, setupRecordText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupQualityPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupQualityPanel({ model }: SetupQualityPanelProps) {
  const setupContext = model.setupContext;
  const qualityComponents = recordSection(setupContext?.metadata_json.quality_components);
  const componentEntries = Object.entries(qualityComponents || {});

  return (
    <Panel title="Quality And Readiness" eyebrow="Context scoring">
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge value={setupContext?.setup_quality_label || "Setup quality unavailable"} tone={toneForQuality(setupContext?.setup_quality_label)} />
          <Badge value={formatPercent(setupContext?.setup_quality_score)} tone="info" />
          {model.readiness && (
            <>
              <Badge value={model.readiness.assessment.readiness_label} tone={toneForQuality(model.readiness.assessment.readiness_label)} />
              <Badge value={formatPercent(model.readiness.assessment.readiness_score)} tone="info" />
            </>
          )}
        </div>
        {model.readiness ? (
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{model.readiness.assessment.summary}</p>
        ) : (
          <SetupEmptySection title="Readiness unavailable" message="No decision-readiness payload was returned for this signal." />
        )}
        {componentEntries.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2">
            {componentEntries.map(([name, value]) => {
              const record = recordSection(value);
              return (
                <div key={name} className="muted-surface rounded-lg p-4">
                  <p className="text-xs font-medium uppercase text-slate-500">{setupLabel(name)}</p>
                  <p className="mt-2 text-lg font-semibold text-[var(--strong)]">{formatPercent(record?.score as string)}</p>
                  <p className="mt-1 text-xs text-slate-500">Weight {formatPercent(record?.weight as string)}</p>
                </div>
              );
            })}
          </div>
        )}
        {model.readiness && model.readiness.blockers.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-[var(--strong)]">Readiness Blockers</h3>
            {model.readiness.blockers.map((blocker, index) => (
              <div key={`blocker-${index}`} className="muted-surface rounded-lg p-3 text-sm">
                {setupRecordText(blocker)}
              </div>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}
