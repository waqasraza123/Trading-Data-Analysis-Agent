export function TriageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="surface rounded-lg p-5">
        <div className="h-5 w-40 rounded bg-slate-200 dark:bg-slate-800" />
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-20 rounded-lg bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-3 2xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} className="h-80 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)]" />
        ))}
      </div>
    </div>
  );
}
