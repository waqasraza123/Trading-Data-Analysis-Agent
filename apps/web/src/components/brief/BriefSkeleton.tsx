import { AppShell } from "@/components/layout/app-shell";

export function BriefSkeleton() {
  return (
    <AppShell appName="Daily Trading Dashboard">
      <div className="space-y-6">
        <div className="h-28 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
          {Array.from({ length: 7 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="space-y-6">
            <div className="h-96 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
            <div className="h-80 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
          </div>
          <div className="space-y-6">
            <div className="h-72 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
            <div className="h-72 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
