import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function QualityLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-4/5 rounded-md" />
        </div>
        <ShimmerSkeleton className="h-10 w-52 rounded-md" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-24 rounded-xl" />
          ))}
        </div>
        <ShimmerSkeleton className="h-16 rounded-lg" />
        <ShimmerSkeleton className="h-28 rounded-lg" />
        <ShimmerSkeleton className="h-28 rounded-lg" />
        <ShimmerSkeleton className="h-32 rounded-lg" />
        <ShimmerSkeleton className="h-28 rounded-lg" />
        <ShimmerSkeleton className="h-20 rounded-lg" />
        <ShimmerSkeleton className="h-40 rounded-lg" />
      </section>
    </RouteLoadingShell>
  );
}
