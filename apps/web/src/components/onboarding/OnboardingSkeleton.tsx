import { ShimmerSkeleton } from "@/lib/ui/motion";

export function OnboardingSkeleton() {
  return (
    <div className="space-y-4">
      <ShimmerSkeleton className="h-32 rounded-lg" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <div className="space-y-4">
          <ShimmerSkeleton className="h-36 rounded-lg" />
          <ShimmerSkeleton className="h-96 rounded-lg" />
        </div>
        <ShimmerSkeleton className="h-72 rounded-lg" />
      </div>
    </div>
  );
}
