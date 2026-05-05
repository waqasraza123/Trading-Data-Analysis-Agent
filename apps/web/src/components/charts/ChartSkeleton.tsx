export function ChartSkeleton() {
  return (
    <div className="min-h-80 animate-pulse rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
      <div className="h-4 w-40 rounded bg-slate-300/60 dark:bg-slate-700" />
      <div className="mt-8 grid h-56 grid-cols-12 items-end gap-2">
        {Array.from({ length: 36 }, (_, index) => (
          <div
            key={index}
            className="rounded-t bg-slate-300/60 dark:bg-slate-700"
            style={{ height: `${24 + ((index * 17) % 70)}%` }}
          />
        ))}
      </div>
    </div>
  );
}
