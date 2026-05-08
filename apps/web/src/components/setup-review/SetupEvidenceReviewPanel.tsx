import { Badge, toneForQuality } from "@/components/status/badge";
import type { JsonRecord, SignalRiskNote } from "@/lib/api/types";
import { formatDecimal, formatPercent } from "@/lib/formatting/numbers";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupReviewModel } from "@/lib/setup-review/types";
import { SetupReviewCard, SetupReviewEmpty, SetupReviewSection } from "./SetupReviewSection";

export function SetupEvidenceReviewPanel({ model }: { model: SetupReviewModel }) {
  const riskNotes = [...model.riskNotes, ...(model.setupContext?.risk_notes_json || [])];

  return (
    <SetupReviewSection eyebrow="Evidence and confidence" title="Supporting evidence, conflicts, and risk notes">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          {model.evidenceGroups.length === 0 ? (
            <SetupReviewEmpty title="No evidence rows" message="The backend did not return signal evidence." />
          ) : (
            model.evidenceGroups.map((group, groupIndex) => (
              <AnimatedListItem as="article" key={group.type} style={motionRevealDensityStyle(groupIndex, "compact")}>
                <SetupReviewCard>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-[var(--strong)]">{setupLabel(group.type)}</h3>
                    <Badge value={`${group.supporting.length} supporting`} tone="good" />
                    <Badge value={`${group.conflicting.length} conflicting`} tone="warning" />
                    <Badge value={`${group.neutral.length} neutral`} tone="neutral" />
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    {[...group.supporting, ...group.conflicting, ...group.neutral].slice(0, 6).map((item) => (
                      <div key={item.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3">
                        <div className="flex flex-wrap gap-2">
                          <Badge value={item.direction} tone={item.direction.includes("conflict") ? "warning" : "info"} />
                          <Badge value={`Weight ${formatDecimal(item.weight)}`} tone="neutral" />
                        </div>
                        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(item.message)}</p>
                      </div>
                    ))}
                  </div>
                </SetupReviewCard>
              </AnimatedListItem>
            ))
          )}
        </div>
        <aside className="space-y-4">
          <SetupReviewCard>
            <p className="text-sm font-semibold text-[var(--strong)]">Confidence components</p>
            <div className="mt-3 space-y-3">
              {model.confidenceComponents.length === 0 ? (
                <p className="text-sm text-slate-500">No component scores returned.</p>
              ) : (
                model.confidenceComponents.slice(0, 6).map((component, index) => (
                  <AnimatedListItem as="article" key={component.id} style={motionRevealDensityStyle(index, "compact")}>
                    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-medium text-[var(--strong)]">{setupLabel(component.component_name)}</span>
                        <Badge value={formatPercent(component.weighted_score)} tone="info" />
                      </div>
                      <p className="mt-2 text-xs leading-5 text-slate-500">{sanitizeSetupText(component.reason)}</p>
                    </div>
                  </AnimatedListItem>
                ))
              )}
            </div>
          </SetupReviewCard>
          <SetupReviewCard>
            <p className="text-sm font-semibold text-[var(--strong)]">Risk notes</p>
            <div className="mt-3 space-y-3">
              {riskNotes.length === 0 ? (
                <p className="text-sm text-slate-500">No risk notes returned.</p>
              ) : (
                riskNotes.slice(0, 6).map((note, index) => (
                  <AnimatedListItem as="article" key={riskKey(note, index)} style={motionRevealDensityStyle(index, "compact")}>
                    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-3">
                      <Badge value={riskSeverity(note)} tone={toneForQuality(riskSeverity(note))} />
                      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(riskMessage(note))}</p>
                    </div>
                  </AnimatedListItem>
                ))
              )}
            </div>
          </SetupReviewCard>
        </aside>
      </div>
    </SetupReviewSection>
  );
}

function riskKey(note: SignalRiskNote | JsonRecord, index: number): string {
  return "id" in note && typeof note.id === "string" ? note.id : `risk-${index}`;
}

function riskSeverity(note: SignalRiskNote | JsonRecord): string {
  if ("severity" in note && typeof note.severity === "string") {
    return note.severity;
  }
  if ("code" in note && typeof note.code === "string") {
    return note.code;
  }
  return "risk note";
}

function riskMessage(note: SignalRiskNote | JsonRecord): string {
  const record = note as Record<string, unknown>;
  for (const key of ["message", "reason", "summary", "description"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "Risk context returned.";
}
