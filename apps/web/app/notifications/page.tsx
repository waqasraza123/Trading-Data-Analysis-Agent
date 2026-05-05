import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/empty-states/empty-state";
import { NotificationDetailPanel } from "@/components/notifications/NotificationDetailPanel";
import { NotificationErrorState } from "@/components/notifications/NotificationErrorState";
import { NotificationFilterBar } from "@/components/notifications/NotificationFilterBar";
import { NotificationInboxHeader } from "@/components/notifications/NotificationInboxHeader";
import { NotificationList } from "@/components/notifications/NotificationList";
import {
  ReviewMetricGrid,
  ReviewSurfaceMetric,
} from "@/components/review-surfaces/ReviewSurface";
import { getNotificationInboxData } from "@/lib/api/notifications";

type NotificationsPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function NotificationsPage({ searchParams }: NotificationsPageProps) {
  const params = await searchParams;
  const data = await getNotificationInboxData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <div className="space-y-6">
        <NotificationInboxHeader data={data} />
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before notification events can load."
          />
        ) : (
          <>
            <ReviewMetricGrid>
              <ReviewSurfaceMetric label="Visible events" value={data.events.length} detail="After current filters" tone="info" />
              <ReviewSurfaceMetric label="Unread" value={data.unreadCount} detail="Open inbox items" tone={data.unreadCount > 0 ? "warning" : "good"} />
              <ReviewSurfaceMetric label="Delivery attempts" value={data.attempts.length} detail="For selected event" />
              <ReviewSurfaceMetric label="Workspace" value={data.workspace.name} detail="Current inbox scope" />
            </ReviewMetricGrid>
            <NotificationFilterBar data={data} />
            <NotificationErrorState failures={data.failures} />
            <div className="grid gap-5 xl:grid-cols-[minmax(340px,460px)_minmax(0,1fr)]">
              <NotificationList data={data} />
              <NotificationDetailPanel data={data} />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
