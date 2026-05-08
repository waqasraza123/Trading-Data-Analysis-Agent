import { cn } from "@/lib/ui/cn";

type SkeletonProps = {
  className?: string;
  ariaHidden?: boolean;
};

export function Skeleton({ className, ariaHidden = true }: SkeletonProps) {
  return (
    <div
      aria-hidden={ariaHidden}
      className={cn(
        "motion-shimmer rounded-xl bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)] dark:bg-[color-mix(in_srgb,var(--surface-muted)_78%,transparent)]",
        className,
      )}
    />
  );
}
