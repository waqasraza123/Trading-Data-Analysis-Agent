import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type StatGridProps = {
  children: ReactNode;
  className?: string;
};

export function StatGrid({ children, className }: StatGridProps) {
  return <div className={cn("grid gap-3 sm:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7", className)}>{children}</div>;
}
