import { Badge, toneForQuality } from "@/components/status/badge";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupReasoningReviewPanel({ model }: { model: SetupReviewModel }) {
  const reasoning = model.reasoning;
  const actionItems = model.actionPlanSection?.action_items;
  const actionCount = Array.isArray(actionItems) ? actionItems.length : 0;

  return (
    <SetupReviewSection id="reasoning" eyebrow="Reasoning" title="Scenario hypotheses and backend-safe follow-up">
      {!reasoning ? (
        <SetupReviewEmpty title="Scenario reasoning unavailable" message="No persisted scenario reasoning was returned for this setup." />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Badge value={reasoning.reasoning_run.status} tone={toneForQuality(reasoning.reasoning_run.status)} />
            <Badge value={`Safety ${setupLabel(reasoning.reasoning_run.safety_status)}`} tone={toneForQuality(reasoning.reasoning_run.safety_status)} />
            <Badge value={`Grounding ${setupLabel(reasoning.reasoning_run.grounding_status)}`} tone={toneForQuality(reasoning.reasoning_run.grounding_status)} />
            <Badge value={`${actionCount} backend follow-up items`} tone="info" />
          </div>
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(reasoning.summary)}</p>
          <div className="grid gap-4 lg:grid-cols-2">
            {reasoning.scenarios.map((scenario, index) => (
              <AnimatedListItem as="article" key={`${scenario.scenario_type}-${scenario.scenario_label}`} style={motionRevealDensityStyle(index, "compact")}>
                <SetupReviewCard>
                  <div className="flex flex-wrap gap-2">
                    <Badge value={scenario.scenario_type} tone="info" />
                    <Badge value={scenario.possibility_label} tone={toneForQuality(scenario.possibility_label)} />
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-[var(--strong)]">{sanitizeSetupText(scenario.scenario_label)}</h3>
                  <ScenarioList title="Supporting evidence" items={scenario.supporting_evidence} />
                  <ScenarioList title="Conflicting evidence" items={scenario.conflicting_evidence} />
                  <ScenarioList title="Backend-safe suggested actions" items={scenario.suggested_backend_actions.map(setupLabel)} />
                </SetupReviewCard>
              </AnimatedListItem>
            ))}
          </div>
          {reasoning.limitations.length > 0 && (
            <p className="text-xs leading-5 text-slate-500">Limitations: {reasoning.limitations.map(sanitizeSetupText).join("; ")}</p>
          )}
        </div>
      )}
    </SetupReviewSection>
  );
}

function ScenarioList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{title}</p>
      <ul className="mt-2 space-y-1 text-sm leading-6 text-slate-600 dark:text-slate-300">
        {items.slice(0, 4).map((item) => (
          <li key={item}>{sanitizeSetupText(item)}</li>
        ))}
      </ul>
    </div>
  );
}
