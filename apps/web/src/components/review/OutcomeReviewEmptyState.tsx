import { EmptyState } from "@/components/empty-states/empty-state";

export function OutcomeReviewEmptyState() {
  return (
    <EmptyState
      title="No outcome items to review"
      message="No recent signal outcomes matched the current filters. Run outcome evaluation in the backend or broaden the filters."
    />
  );
}
