import { RouteLoadingShell } from "@/components/layout/RouteLoadingShell";
import { ShimmerSkeleton } from "@/lib/ui/motion";

export default function JournalEntryLoading() {
  return (
    <RouteLoadingShell>
      <section className="space-y-6">
        <ShimmerSkeleton className="h-8 w-64 rounded-md" />
        <div className="grid gap-5 xl:grid-cols-[minmax(380px,460px)_minmax(0,1fr)]">
          <section className="space-y-3">
            <ShimmerSkeleton className="h-12 rounded-lg" />
            <ShimmerSkeleton className="h-52 rounded-lg" />
          </section>
          <section className="space-y-3">
            <ShimmerSkeleton className="h-12 rounded-lg" />
            <ShimmerSkeleton className="h-40 rounded-lg" />
            <ShimmerSkeleton className="h-32 rounded-lg" />
          </section>
        </div>
      </section>
    </RouteLoadingShell>
  );
}
