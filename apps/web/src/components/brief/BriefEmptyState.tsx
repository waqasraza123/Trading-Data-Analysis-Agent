import { EmptyState } from "@/components/empty-states/empty-state";
import type { BriefSectionStatus } from "@/lib/brief/types";

type BriefEmptyStateProps = {
  status: BriefSectionStatus;
  fallbackTitle: string;
  fallbackMessage: string;
};

export function BriefEmptyState({ status, fallbackTitle, fallbackMessage }: BriefEmptyStateProps) {
  return (
    <EmptyState
      title={status.label || fallbackTitle}
      message={status.message || fallbackMessage}
    />
  );
}
