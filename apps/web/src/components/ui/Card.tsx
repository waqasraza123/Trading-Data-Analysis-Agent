import type { ReactNode } from "react";
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
        interactive && "hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--accent)_34%,var(--border))] hover:shadow-glow",
        interactive && "motion-hover-lift",
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
        interactive && "hover:border-[color-mix(in_srgb,var(--accent)_30%,var(--border))] hover:bg-[var(--surface-elevated)]",
        interactive && "motion-hover-lift",
        className,
      )}
    >
      {children}
    </div>
  );
}
