import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

const interactiveFocusClass =
  "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]";

type SurfaceProps = {
  children: ReactNode;
  className?: string;
  muted?: boolean;
  interactive?: boolean;
};

export function Surface({ children, className, muted = false, interactive = false }: SurfaceProps) {
  return (
    <div
      className={cn(
        muted ? "muted-surface" : "surface",
        "motion-card rounded-2xl transition duration-200",
        interactive && [
          "cursor-pointer motion-hover-lift hover:-translate-y-0.5 hover:shadow-glow",
          interactiveFocusClass,
        ],
        className,
      )}
    >
      {children}
    </div>
  );
}
