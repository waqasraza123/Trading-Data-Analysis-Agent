import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";

export default function DashboardLoading() {
  const env = getPublicEnv();
  return (
    <AppShell appName={env.appName}>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="h-28 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
        ))}
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="h-52 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
        ))}
      </div>
    </AppShell>
  );
}
