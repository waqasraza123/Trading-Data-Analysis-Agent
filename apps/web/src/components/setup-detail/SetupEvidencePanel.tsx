import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { SignalEvidence } from "@/lib/api/types";
import { formatDecimal } from "@/lib/formatting/numbers";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import type { SetupDetailViewModel } from "@/lib/setup-detail/types";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SetupEmptySection } from "./SetupEmptySection";

type SetupEvidencePanelProps = {
  model: SetupDetailViewModel;
};

export function SetupEvidencePanel({ model }: SetupEvidencePanelProps) {
  return (
    <Panel title="Evidence" eyebrow="Grouped deterministic inputs">
      {model.evidenceGroups.length === 0 ? (
        <SetupEmptySection title="No evidence rows" message="The backend did not return signal evidence." />
      ) : (
        <div className="space-y-5">
          {model.evidenceGroups.map((group, index) => (
            <AnimatedListItem as="section" key={group.type} style={motionRevealDensityStyle(index, "compact")}>
              <details className="space-y-3 rounded-lg border border-[var(--line)] p-4" open>
                <summary className="flex cursor-pointer flex-wrap items-center gap-2">
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{setupLabel(group.type)}</h3>
                  <Badge value={`${group.supporting.length} supporting`} tone="good" />
                  <Badge value={`${group.conflicting.length} conflicting`} tone="warning" />
                </summary>
                <div className="mt-4 space-y-3">
                  <EvidenceColumn title="Supporting evidence" evidence={group.supporting} startIndex={0} />
                  <EvidenceColumn title="Conflicting evidence" evidence={group.conflicting} startIndex={group.supporting.length} />
                  <EvidenceColumn title="Neutral evidence" evidence={group.neutral} startIndex={group.supporting.length + group.conflicting.length} />
                </div>
              </details>
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}

function EvidenceColumn({
  title,
  evidence,
  startIndex,
}: {
  title: string;
  evidence: SignalEvidence[];
  startIndex: number;
}) {
  if (evidence.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold uppercase text-slate-500">{title}</p>
      <div className="grid gap-3 md:grid-cols-2">
        {evidence.map((item, index) => (
          <AnimatedListItem
            as="article"
            key={item.id}
            style={motionRevealDensityStyle(startIndex + index, "compact")}
          >
            <div className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge value={item.direction} tone="info" />
                <span className="text-xs text-slate-500">Weight {formatDecimal(item.weight)}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{sanitizeSetupText(item.message)}</p>
              {item.numeric_value && <p className="mt-2 text-xs text-slate-500">Value {formatDecimal(item.numeric_value)}</p>}
            </div>
          </AnimatedListItem>
        ))}
      </div>
    </div>
  );
}
