import { Badge, toneForQuality } from "@/components/status/badge";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupLabel, setupRecordText, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupIntelligenceContextPanel({ model }: { model: SetupReviewModel }) {
  const hasContent = Boolean(model.quality || model.multiTimeframeContext || model.crossAssetContext || model.crossAssetResults.length);

  return (
    <SetupReviewSection eyebrow="Quality gates" title="Multi-timeframe and cross-asset context">
      {!hasContent ? (
        <SetupReviewEmpty title="Context intelligence unavailable" message="No quality, multi-timeframe, or cross-asset context was returned." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {model.quality && (
            <SetupReviewCard>
              <p className="text-sm font-semibold text-[var(--strong)]">Quality gate</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={model.quality.quality_run.quality_label} tone={toneForQuality(model.quality.quality_run.quality_label)} />
                <Badge value={model.quality.quality_run.status} tone={toneForQuality(model.quality.quality_run.status)} />
                <Badge value={formatPercent(model.quality.quality_run.quality_score)} tone="info" />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(model.quality.quality_run.summary)}</p>
              {model.quality.findings.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">{model.quality.findings.length} quality findings returned for review.</p>
              )}
            </SetupReviewCard>
          )}
          {model.multiTimeframeContext && (
            <SetupReviewCard>
              <p className="text-sm font-semibold text-[var(--strong)]">Multi-timeframe context</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={model.multiTimeframeContext.agreement_label} tone={toneForQuality(model.multiTimeframeContext.agreement_label)} />
                <Badge value={formatPercent(model.multiTimeframeContext.agreement_score)} tone="info" />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(model.multiTimeframeContext.context_summary)}</p>
              {model.multiTimeframeContext.warnings_json.slice(0, 2).map((warning, index) => (
                <AnimatedListItem
                  as="p"
                  key={`mtf-warning-${index}`}
                  style={motionRevealDensityStyle(index, "compact")}
                  className="mt-2 text-xs text-slate-500"
                >
                  {setupRecordText(warning)}
                </AnimatedListItem>
              ))}
            </SetupReviewCard>
          )}
          {(model.crossAssetContext || model.crossAssetResults.length > 0) && (
            <SetupReviewCard>
              <p className="text-sm font-semibold text-[var(--strong)]">Cross-asset context</p>
              {model.crossAssetContext && (
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(model.crossAssetContext.summary)}</p>
              )}
              <div className="mt-3 space-y-2">
                {model.crossAssetResults.slice(0, 4).map((result, index) => (
                  <AnimatedListItem as="article" key={result.id} style={motionRevealDensityStyle(index, "compact")}>
                    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3">
                    <div className="flex flex-wrap gap-2">
                      <Badge value={setupLabel(result.alignment_label)} tone={toneForQuality(result.alignment_label)} />
                      <Badge value={setupLabel(result.lead_lag_label)} tone="info" />
                      <Badge value={setupLabel(result.data_quality_label)} tone={toneForQuality(result.data_quality_label)} />
                    </div>
                    </div>
                  </AnimatedListItem>
                ))}
              </div>
            </SetupReviewCard>
          )}
        </div>
      )}
    </SetupReviewSection>
  );
}
