import type { NotificationFailure } from "@/lib/notifications/types";

type NotificationErrorStateProps = {
  failures: NotificationFailure[];
};

export function NotificationErrorState({ failures }: NotificationErrorStateProps) {
  const visibleFailures = failures.filter((failure) => !failure.missing);
  if (visibleFailures.length === 0) {
    return null;
  }
  return (
    <div className="rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] p-4 text-sm">
      <h3 className="font-semibold text-[var(--danger)]">Notification data needs review</h3>
      <div className="mt-3 grid gap-2">
        {visibleFailures.map((failure) => (
          <div key={`${failure.label}-${failure.status}`} className="text-[var(--danger)]">
            <span className="font-medium">{failure.label}</span>: {failure.message}
          </div>
        ))}
      </div>
    </div>
  );
}
