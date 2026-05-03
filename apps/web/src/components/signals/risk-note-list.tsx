import { EmptyState } from "@/components/empty-states/empty-state";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { SignalRiskNote } from "@/lib/api/types";

export function RiskNoteList({ notes }: { notes: SignalRiskNote[] }) {
  if (notes.length === 0) {
    return <EmptyState title="No risk notes" message="The backend did not return additional risk context." />;
  }

  return (
    <div className="space-y-3">
      {notes.map((note) => (
        <div key={note.id} className="muted-surface rounded-lg p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={note.severity} tone={toneForQuality(note.severity)} />
            <span className="text-xs font-medium uppercase text-slate-500">{note.code}</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--strong)]">{note.message}</p>
        </div>
      ))}
    </div>
  );
}
