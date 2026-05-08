import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function StrategyPreferenceLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
          <div className="flex flex-wrap gap-2 pt-1">
            <ShimmerSkeleton className="h-6 w-32 rounded-full" />
            <ShimmerSkeleton className="h-6 w-40 rounded-full" />
          </div>
        </div>
        <ShimmerSkeleton className="h-20 rounded-xl" />
        <ShimmerSkeleton className="h-20 rounded-xl" />
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_460px]">
          <ShimmerSkeleton className="h-56 rounded-xl" />
          <ShimmerSkeleton className="h-72 rounded-xl" />
        </div>
      </section>
    </RouteLoadingShell>
  );
}
