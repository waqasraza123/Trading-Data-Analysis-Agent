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
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getNotificationInboxData } from "@/lib/api/notifications";

type NotificationsPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function NotificationsPage({ searchParams }: NotificationsPageProps) {
  const params = await searchParams;
  const data = await getNotificationInboxData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <NotificationInboxHeader data={data} />
        </AnimatedListItem>
        {!data.workspace ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <EmptyState
              title="No workspace available"
              message="Seed or create a workspace in the API before notification events can load."
            />
          </AnimatedListItem>
        ) : (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "regular")}>
              <ReviewMetricGrid>
                <ReviewSurfaceMetric label="Visible events" value={data.events.length} detail="After current filters" tone="info" />
                <ReviewSurfaceMetric label="Unread" value={data.unreadCount} detail="Open inbox items" tone={data.unreadCount > 0 ? "warning" : "good"} />
                <ReviewSurfaceMetric label="Delivery attempts" value={data.attempts.length} detail="For selected event" />
                <ReviewSurfaceMetric label="Workspace" value={data.workspace.name} detail="Current inbox scope" />
              </ReviewMetricGrid>
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
              <NotificationFilterBar data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <NotificationErrorState failures={data.failures} />
            </AnimatedListItem>
            <div className="grid gap-5 xl:grid-cols-[minmax(340px,460px)_minmax(0,1fr)]">
              <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
                <NotificationList data={data} />
              </AnimatedListItem>
              <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
                <NotificationDetailPanel data={data} />
              </AnimatedListItem>
            </div>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
