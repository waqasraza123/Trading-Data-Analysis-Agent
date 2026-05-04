import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import { formatPercent } from "@/lib/formatting/numbers";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupBiasSummaryProps = {
  model: SetupDetailViewModel;
};

export function SetupBiasSummary({ model }: SetupBiasSummaryProps) {
  const setupContext = model.setupContext;
  const signal = model.signal?.signal || null;

  return (
    <Panel title="Setup Context" eyebrow="Deterministic review summary">
      {!setupContext && !signal ? (
        <SetupEmptySection title="Setup context unavailable" message="No signal or setup context payload was returned." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={setupContext?.directional_bias || signal?.bias} tone={toneForBias(setupContext?.directional_bias || signal?.bias)} />
            <Badge value={setupContext?.setup_quality_label || "Quality unavailable"} tone={toneForQuality(setupContext?.setup_quality_label)} />
            <Badge value={formatPercent(setupContext?.setup_quality_score)} tone="info" />
            <Badge value={setupContext?.status || signal?.classification_status} tone={toneForQuality(setupContext?.status || signal?.classification_status)} />
          </div>
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            {setupContext?.summary || signal?.summary || signal?.no_signal_reason || "No setup context summary returned."}
          </p>
          <dl className="grid gap-3 text-sm md:grid-cols-3">
            <Detail label="Directional bias" value={setupContext?.directional_bias || signal?.bias || "Not available"} />
            <Detail label="Pattern" value={signal?.pattern_type || "No pattern"} />
            <Detail label="Classification" value={signal?.classification_status || "Not available"} />
          </dl>
        </div>
      )}
    </Panel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-2 text-sm font-semibold text-[var(--strong)]">{value}</dd>
    </div>
  );
}
