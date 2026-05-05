export function CommandCenterSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-80 animate-pulse rounded-3xl border border-white/70 bg-slate-100 shadow-[0_30px_100px_rgba(15,23,42,0.08)] dark:border-slate-800 dark:bg-slate-900" />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.7fr)]">
        <div className="space-y-6">
          <SkeletonPanel />
          <SkeletonPanel />
          <SkeletonPanel />
        </div>
        <div className="space-y-6">
          <SkeletonPanel />
          <SkeletonPanel />
          <SkeletonPanel />
        </div>
      </div>
    </div>
  );
}

function SkeletonPanel() {
  return (
    <section className="rounded-3xl border border-white/70 bg-white/80 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.08)] dark:border-slate-800 dark:bg-slate-950/70">
      <div className="space-y-4">
        <div className="h-4 w-1/3 animate-pulse rounded-full bg-slate-100 dark:bg-slate-800" />
        <div className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
        <div className="h-20 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-900" />
      </div>
    </section>
  );
}
