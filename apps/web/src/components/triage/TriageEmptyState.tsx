import { EmptyState } from "@/components/empty-states/empty-state";

export function TriageEmptyState() {
  return (
    <EmptyState
      title="No setups match this review scope"
      message="No stored deterministic setup context matched the current workspace and filters."
    />
  );
}
