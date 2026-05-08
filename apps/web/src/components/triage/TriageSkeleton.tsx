import { ShimmerSkeleton } from "@/lib/ui/motion";

export function TriageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="surface rounded-lg p-5">
        <ShimmerSkeleton className="h-5 w-40" />
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <ShimmerSkeleton key={index} className="h-20 rounded-lg" />
          ))}
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-3 2xl:grid-cols-6">
        {Array.from({ length: 6 }).map((_, index) => (
          <ShimmerSkeleton key={index} className="h-80 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)]/70" />
        ))}
      </div>
    </div>
  );
}
