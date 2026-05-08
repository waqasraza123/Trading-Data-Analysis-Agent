import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function DashboardLoading() {
  const env = getPublicEnv();
  return (
    <AppShell appName={env.appName}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <ShimmerSkeleton key={index} className="h-28 rounded-lg bg-slate-200/70 dark:bg-slate-800/70" />
        ))}
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <ShimmerSkeleton key={index} className="h-52 rounded-lg bg-slate-200/70 dark:bg-slate-800/70" />
        ))}
      </div>
    </AppShell>
  );
}
