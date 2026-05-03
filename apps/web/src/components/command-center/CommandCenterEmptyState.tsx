import { EmptyState } from "@/components/empty-states/empty-state";

export function CommandCenterEmptyState() {
  return (
    <EmptyState
      title="No workspace available"
      message="Seed or create a workspace in the API before the daily command center can load."
    />
  );
}
