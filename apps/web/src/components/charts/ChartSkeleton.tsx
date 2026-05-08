import { ShimmerSkeleton } from "@/lib/ui/motion";

export function ChartSkeleton() {
  return (
    <ShimmerSkeleton className="min-h-80 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)]/70 p-4">
      <ShimmerSkeleton className="h-4 w-40 rounded" />
      <div className="mt-8 grid h-56 grid-cols-12 items-end gap-2">
        {Array.from({ length: 36 }, (_, index) => (
          <ShimmerSkeleton
            key={index}
            className="rounded-t bg-slate-300/30 dark:bg-slate-700/40"
            style={{ height: `${24 + ((index * 17) % 70)}%` }}
          />
        ))}
      </div>
    </ShimmerSkeleton>
  );
}
