import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

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
        "motion-card rounded-2xl",
        interactive && "transition duration-200 hover:-translate-y-0.5 hover:shadow-glow",
        interactive && "motion-hover-lift",
        className,
      )}
    >
      {children}
    </div>
  );
}
