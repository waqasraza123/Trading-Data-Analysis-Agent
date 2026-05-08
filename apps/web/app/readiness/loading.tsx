import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function ReadinessLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-20 rounded-xl" />
          ))}
        </div>
        <ShimmerSkeleton className="h-52 rounded-xl" />
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <ShimmerSkeleton className="h-80 rounded-xl" />
          <section className="space-y-6">
            <ShimmerSkeleton className="h-20 rounded-xl" />
            <ShimmerSkeleton className="h-44 rounded-xl" />
          </section>
        </div>
      </section>
    </RouteLoadingShell>
  );
}
