import { cn } from "@/lib/ui/cn";
import { ShimmerSkeleton } from "./motion";

type SkeletonProps = {
  className?: string;
  ariaHidden?: boolean;
};

export function Skeleton({ className, ariaHidden = true }: SkeletonProps) {
  return (
    <ShimmerSkeleton
      ariaHidden={ariaHidden}
      className={cn(
        "bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)] dark:bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)]",
        className,
      )}
    />
  );
}
