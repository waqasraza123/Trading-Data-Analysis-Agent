import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function SignalDetailLoading() {
  return (
    <RouteLoadingShell>
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
    </RouteLoadingShell>
  );
}
