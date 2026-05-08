import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function OutcomeReviewLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-60 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-24 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <ShimmerSkeleton className="h-14 rounded-lg" />
          <ShimmerSkeleton className="h-14 rounded-lg" />
        </div>
        <ShimmerSkeleton className="h-16 rounded-lg" />
        <ShimmerSkeleton className="h-16 rounded-lg" />
        <div className="grid gap-3">
          {Array.from({ length: 8 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-16 rounded-lg" />
          ))}
        </div>
      </section>
    </AppShell>
  );
}
