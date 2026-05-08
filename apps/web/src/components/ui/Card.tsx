import type { ReactNode } from "react";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";
import { cn } from "@/lib/ui/cn";

type CardProps = {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
};

export function Card({ children, className, interactive = false }: CardProps) {
  return (
    <div
      className={cn(
        "surface motion-card rounded-2xl p-5 transition duration-200",
        interactive && [
          "cursor-pointer",
          "hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--accent)_34%,var(--border))] hover:shadow-glow",
          MOTION_INTERACTIVE_CLASS,
        ],
        className,
      )}
    >
      {children}
    </div>
  );
}

export function MutedCard({ children, className, interactive = false }: CardProps) {
  return (
    <div
      className={cn(
        "muted-surface motion-card rounded-2xl p-4 transition duration-200",
        interactive && [
          "cursor-pointer",
          "hover:border-[color-mix(in_srgb,var(--accent)_30%,var(--border))] hover:bg-[var(--surface-elevated)]",
          MOTION_INTERACTIVE_CLASS,
        ],
        className,
      )}
    >
      {children}
    </div>
  );
}
