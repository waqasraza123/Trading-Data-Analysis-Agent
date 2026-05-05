import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

type ActionBarProps = {
  children: ReactNode;
  className?: string;
};

export function ActionBar({ children, className }: ActionBarProps) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2 rounded-2xl border border-[var(--border)] bg-[var(--surface-muted)] p-2", className)}>
      {children}
    </div>
  );
}
