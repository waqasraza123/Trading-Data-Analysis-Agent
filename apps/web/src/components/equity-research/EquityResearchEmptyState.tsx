export function EquityResearchEmptyState({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="muted-surface rounded-lg border border-dashed border-[var(--line)] p-5">
      <h2 className="text-base font-semibold text-[var(--strong)]">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-500">{message}</p>
    </div>
  );
}
