import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function NotificationsLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <div className="space-y-3">
          <ShimmerSkeleton className="h-7 w-72 rounded-md" />
          <ShimmerSkeleton className="h-4 w-3/5 rounded-md" />
          <div className="flex flex-wrap gap-2">
            <ShimmerSkeleton className="h-8 w-36 rounded-full" />
            <ShimmerSkeleton className="h-8 w-28 rounded-full" />
            <ShimmerSkeleton className="h-8 w-44 rounded-full" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-28 rounded-xl" />
          ))}
        </div>
        <div className="grid gap-3 md:grid-cols-[minmax(340px,460px)_minmax(0,1fr)]">
          <ShimmerSkeleton className="h-10 rounded-lg" />
          <ShimmerSkeleton className="h-10 rounded-lg" />
        </div>
        <div className="grid gap-5 xl:grid-cols-[minmax(340px,460px)_minmax(0,1fr)]">
          <section className="space-y-3">
            {Array.from({ length: 7 }).map((_, index) => (
              <ShimmerSkeleton key={index} className="h-16 rounded-lg" />
            ))}
          </section>
          <section className="space-y-3">
            <ShimmerSkeleton className="h-12 rounded-lg" />
            <ShimmerSkeleton className="h-56 rounded-lg" />
          </section>
        </div>
      </section>
    </RouteLoadingShell>
  );
}
