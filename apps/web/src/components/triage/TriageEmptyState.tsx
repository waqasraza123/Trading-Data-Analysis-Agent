import { EmptyState } from "@/components/empty-states/empty-state";

export function TriageEmptyState() {
  return (
    <EmptyState
      title="No triage candidates"
      message="No deterministic signals matched the current workspace and filter set."
    />
  );
}
