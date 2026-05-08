import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function DemoLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-8 w-52 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
        </div>
        <ShimmerSkeleton className="h-56 rounded-xl" />
        <div className="grid gap-4 sm:grid-cols-2">
          <ShimmerSkeleton className="h-40 rounded-xl" />
          <ShimmerSkeleton className="h-40 rounded-xl" />
        </div>
        <ShimmerSkeleton className="h-16 rounded-lg" />
      </section>
    </RouteLoadingShell>
  );
}
