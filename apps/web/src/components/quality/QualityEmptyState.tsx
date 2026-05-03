import { EmptyState } from "@/components/empty-states/empty-state";
import { noDataMessage } from "@/lib/quality/labels";

export function QualityEmptyState() {
  return (
    <EmptyState
      title="No quality diagnostics returned"
      message={noDataMessage()}
    />
  );
}
