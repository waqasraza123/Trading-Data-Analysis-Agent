import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function JournalLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
          <div className="flex flex-wrap gap-2">
            <ShimmerSkeleton className="h-7 w-40 rounded-md" />
            <ShimmerSkeleton className="h-7 w-24 rounded-md" />
            <ShimmerSkeleton className="h-7 w-28 rounded-md" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-24 rounded-xl" />
          ))}
        </div>
        <ShimmerSkeleton className="h-10 w-1/2 rounded-md" />
        <div className="grid gap-3 xl:grid-cols-[minmax(380px,460px)_minmax(0,1fr)]">
          <section className="space-y-3">
            <ShimmerSkeleton className="h-12 rounded-lg" />
            {Array.from({ length: 6 }).map((_, index) => (
              <ShimmerSkeleton key={index} className="h-20 rounded-lg" />
            ))}
          </section>
          <section className="space-y-3">
            <ShimmerSkeleton className="h-12 rounded-lg" />
            {Array.from({ length: 8 }).map((_, index) => (
              <ShimmerSkeleton key={index} className="h-16 rounded-lg" />
            ))}
          </section>
        </div>
      </section>
    </AppShell>
  );
}
