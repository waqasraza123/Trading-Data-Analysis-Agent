import { cn } from "@/lib/ui/cn";

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return <div className={cn("animate-pulse rounded-xl bg-slate-200/80 dark:bg-slate-800/80", className)} />;
}
