import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

const interactiveFocusClass =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]";

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
          "cursor-pointer motion-hover-lift",
          "hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--accent)_34%,var(--border))] hover:shadow-glow",
          interactiveFocusClass,
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
          "cursor-pointer motion-hover-lift",
          "hover:border-[color-mix(in_srgb,var(--accent)_30%,var(--border))] hover:bg-[var(--surface-elevated)]",
          interactiveFocusClass,
        ],
        className,
      )}
    >
      {children}
    </div>
  );
}
