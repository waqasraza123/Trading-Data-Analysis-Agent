import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupReasoningPanelProps = {
  model: SetupDetailViewModel;
};

export function SetupReasoningPanel({ model }: SetupReasoningPanelProps) {
  const reasoning = model.reasoning;

  return (
    <Panel title="Scenario Reasoning" eyebrow="Grounded hypotheses">
      {!reasoning ? (
        <SetupEmptySection title="Scenario reasoning unavailable" message="No persisted scenario reasoning was returned for this signal." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={reasoning.reasoning_run.status} tone={toneForQuality(reasoning.reasoning_run.status)} />
            <Badge value={reasoning.reasoning_run.safety_status} tone={toneForQuality(reasoning.reasoning_run.safety_status)} />
            <Badge value={reasoning.reasoning_run.grounding_status} tone={toneForQuality(reasoning.reasoning_run.grounding_status)} />
          </div>
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(reasoning.summary)}</p>
          <div className="space-y-3">
            {reasoning.scenarios.map((scenario) => (
              <details key={`${scenario.scenario_type}-${scenario.scenario_label}`} className="muted-surface rounded-lg p-4">
                <summary className="cursor-pointer">
                  <span className="inline-flex flex-wrap gap-2">
                  <Badge value={scenario.scenario_type} tone="info" />
                  <Badge value={scenario.possibility_label} tone={toneForQuality(scenario.possibility_label)} />
                  </span>
                  <h3 className="mt-3 text-sm font-semibold text-[var(--strong)]">{sanitizeSetupText(scenario.scenario_label)}</h3>
                </summary>
                {scenario.supporting_evidence.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Supporting: {scenario.supporting_evidence.map(sanitizeSetupText).join("; ")}
                  </p>
                )}
                {scenario.conflicting_evidence.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Conflicting: {scenario.conflicting_evidence.map(sanitizeSetupText).join("; ")}
                  </p>
                )}
                {scenario.suggested_backend_actions.length > 0 && (
                  <p className="mt-2 text-xs text-slate-500">
                    Backend-safe actions: {scenario.suggested_backend_actions.map(setupLabel).join(", ")}
                  </p>
                )}
              </details>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
