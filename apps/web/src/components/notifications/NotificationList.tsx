import type { NotificationInboxData } from "@/lib/notifications/types";
import { NotificationCard } from "./NotificationCard";
import { NotificationEmptyState } from "./NotificationEmptyState";

export function NotificationList({ data }: { data: NotificationInboxData }) {
  if (data.events.length === 0) {
    return <NotificationEmptyState />;
  }
  return (
    <div className="grid gap-3">
      {data.events.map((event) => (
        <NotificationCard
          key={event.id}
          event={event}
          filters={data.filters}
          selected={data.selectedEvent?.id === event.id}
        />
      ))}
    </div>
  );
}
