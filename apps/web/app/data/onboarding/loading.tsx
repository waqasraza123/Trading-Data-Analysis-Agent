import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function DataOnboardingLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-2/3 rounded-md" />
        </div>
        <ShimmerSkeleton className="h-14 w-40 rounded-md" />
        <ShimmerSkeleton className="h-[520px] rounded-xl" />
      </section>
    </AppShell>
  );
}
