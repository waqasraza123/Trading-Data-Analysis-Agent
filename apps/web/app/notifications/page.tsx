import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/empty-states/empty-state";
import { NotificationDetailPanel } from "@/components/notifications/NotificationDetailPanel";
import { NotificationErrorState } from "@/components/notifications/NotificationErrorState";
import { NotificationFilterBar } from "@/components/notifications/NotificationFilterBar";
import { NotificationInboxHeader } from "@/components/notifications/NotificationInboxHeader";
import { NotificationList } from "@/components/notifications/NotificationList";
import { getNotificationInboxData } from "@/lib/api/notifications";

type NotificationsPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function NotificationsPage({ searchParams }: NotificationsPageProps) {
  const params = await searchParams;
  const data = await getNotificationInboxData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <NotificationInboxHeader data={data} />
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before notification events can load."
          />
        ) : (
          <>
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
