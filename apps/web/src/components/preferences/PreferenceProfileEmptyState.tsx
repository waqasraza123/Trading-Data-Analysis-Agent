export function PreferenceProfileEmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="surface rounded-lg p-6">
      <p className="text-xs font-semibold uppercase text-slate-500">Preferences</p>
      <h2 className="mt-2 text-xl font-semibold text-[var(--strong)]">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
        {message}
      </p>
    </div>
  );
}
