import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function SetupLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-64 rounded-md" />
          <ShimmerSkeleton className="h-4 w-2/3 rounded-md" />
        </div>
        <ShimmerSkeleton className="h-10 w-56 rounded-md" />
        <ShimmerSkeleton className="h-[460px] rounded-xl" />
      </section>
    </AppShell>
  );
}
