import { EmptyState } from "@/components/empty-states/empty-state";

export function JournalEmptyState() {
  return (
    <EmptyState
      title="No journal entries"
      message="Create a note when reviewing a signal, setup context, or observed outcome. Notes are for reflection and learning only."
    />
  );
}
