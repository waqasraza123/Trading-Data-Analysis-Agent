import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { ReviewSurfaceHero } from "@/components/review-surfaces/ReviewSurface";
import type { NotificationInboxData } from "@/lib/notifications/types";

export function NotificationInboxHeader({ data }: { data: NotificationInboxData }) {
  return (
    <ReviewSurfaceHero
      eyebrow="Notification inbox"
      title="Review events"
      description="Review backend-safe intelligence events, source context, delivery attempts, and redaction status inside the product."
      actions={
        <>
        <Metric label="Unread" value={data.unreadCount} />
        <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review", "journal"]} />
      </>
      }
    />
  );
}
