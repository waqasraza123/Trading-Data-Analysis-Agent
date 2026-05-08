import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function ScannerLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <ShimmerSkeleton className="h-52 rounded-3xl" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-6">
            {Array.from({ length: 6 }).map((_, index) => (
              <ShimmerSkeleton key={`left-${index}`} className="h-44 rounded-xl" />
            ))}
          </div>
          <div className="space-y-6">
            <ShimmerSkeleton className="h-72 rounded-xl" />
            <ShimmerSkeleton className="h-80 rounded-xl" />
            <ShimmerSkeleton className="h-72 rounded-xl" />
          </div>
        </div>
        <ShimmerSkeleton className="h-64 rounded-xl" />
        <ShimmerSkeleton className="h-16 rounded-lg" />
      </section>
    </RouteLoadingShell>
  );
}
