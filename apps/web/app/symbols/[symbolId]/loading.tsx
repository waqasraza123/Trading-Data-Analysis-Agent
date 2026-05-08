import { AppShell } from "@/components/layout/AppShell";
import { getPublicEnv } from "@/config/env";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function SymbolDetailLoading() {
  const env = getPublicEnv();

  return (
    <AppShell appName={env.appName}>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-64 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <ShimmerSkeleton className="h-10 rounded-lg" />
          <ShimmerSkeleton className="h-10 rounded-lg" />
        </div>
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_360px]">
          <ShimmerSkeleton className="h-80 rounded-xl" />
          <section className="space-y-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <ShimmerSkeleton key={index} className="h-16 rounded-xl" />
            ))}
          </section>
        </div>
      </section>
    </AppShell>
  );
}
