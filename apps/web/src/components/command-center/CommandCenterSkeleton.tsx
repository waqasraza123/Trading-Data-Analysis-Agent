import { Panel } from "@/components/layout/panel";

export function CommandCenterSkeleton() {
  return (
    <div className="space-y-6">
      <div className="h-32 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-900" />
      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_390px]">
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
    <Panel>
      <div className="space-y-3">
        <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100 dark:bg-slate-900" />
        <div className="h-16 animate-pulse rounded bg-slate-100 dark:bg-slate-900" />
        <div className="h-16 animate-pulse rounded bg-slate-100 dark:bg-slate-900" />
      </div>
    </Panel>
  );
}
