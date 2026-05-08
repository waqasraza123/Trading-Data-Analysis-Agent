import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function EquityResearchLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-4/5 rounded-md" />
        </div>
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_440px]">
          <div className="space-y-6">
            <ShimmerSkeleton className="h-28 rounded-xl" />
            <ShimmerSkeleton className="h-24 rounded-xl" />
            <ShimmerSkeleton className="h-40 rounded-xl" />
            <ShimmerSkeleton className="h-52 rounded-xl" />
          </div>
          <div className="space-y-6">
            <ShimmerSkeleton className="h-36 rounded-xl" />
            <ShimmerSkeleton className="h-32 rounded-xl" />
            <ShimmerSkeleton className="h-48 rounded-xl" />
            <ShimmerSkeleton className="h-28 rounded-xl" />
          </div>
        </div>
      </section>
    </RouteLoadingShell>
  );
}
