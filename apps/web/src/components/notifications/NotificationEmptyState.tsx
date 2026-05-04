type NotificationEmptyStateProps = {
  title?: string;
  message?: string;
};

export function NotificationEmptyState({
  title = "No notification events",
  message = "Backend-safe intelligence events will appear here when they are created for this workspace.",
}: NotificationEmptyStateProps) {
  return (
    <div className="muted-surface rounded-lg p-6">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}
