import { cn } from "@/lib/ui/cn";

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "motion-shimmer rounded-xl bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)] dark:bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)]",
        className,
      )}
    />
  );
}
