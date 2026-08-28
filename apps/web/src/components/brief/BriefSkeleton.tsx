import { AppShell } from "@/components/layout/AppShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export function BriefSkeleton() {
  return (
    <AppShell appName="AI Trading SaaS Starter Kit">
      <div className="space-y-6">
        <ShimmerSkeleton className="h-80 rounded-3xl border border-white/70 bg-slate-100/70 shadow-[0_30px_100px_rgba(15,23,42,0.08)] dark:border-slate-800 dark:bg-slate-900/70" />
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
          <div className="space-y-6">
            <ShimmerSkeleton className="h-96 rounded-3xl bg-slate-100/70 dark:bg-slate-900/70" />
            <ShimmerSkeleton className="h-80 rounded-3xl bg-slate-100/70 dark:bg-slate-900/70" />
          </div>
          <div className="space-y-6">
            <ShimmerSkeleton className="h-72 rounded-3xl bg-slate-100/70 dark:bg-slate-900/70" />
            <ShimmerSkeleton className="h-72 rounded-3xl bg-slate-100/70 dark:bg-slate-900/70" />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
