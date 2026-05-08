import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { SignalRiskNote } from "@/lib/api/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function RiskNoteList({ notes }: { notes: SignalRiskNote[] }) {
  if (notes.length === 0) {
    return <EmptyState title="No risk notes" message="The backend did not return additional risk context." />;
  }

  return (
    <div className="space-y-3">
      {notes.map((note, index) => (
        <AnimatedListItem
          as="section"
          key={note.id}
          className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
          style={motionRevealDensityStyle(index, "compact")}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={note.severity} tone={toneForQuality(note.severity)} />
            <span className="text-xs font-medium uppercase text-slate-500">{note.code}</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{note.message}</p>
        </AnimatedListItem>
      ))}
    </div>
  );
}
