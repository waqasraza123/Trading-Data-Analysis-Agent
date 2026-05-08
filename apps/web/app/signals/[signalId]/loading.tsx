import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function SignalDetailLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <ShimmerSkeleton className="h-12 rounded-md" />
          <ShimmerSkeleton className="h-12 rounded-md" />
        </div>
        <ShimmerSkeleton className="h-80 rounded-xl" />
        <div className="grid gap-5 2xl:grid-cols-2">
          <ShimmerSkeleton className="h-52 rounded-xl" />
          <ShimmerSkeleton className="h-52 rounded-xl" />
        </div>
        <ShimmerSkeleton className="h-72 rounded-xl" />
      </section>
    </AppShell>
  );
}
