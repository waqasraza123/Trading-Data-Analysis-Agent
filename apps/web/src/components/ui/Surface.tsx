import type { ReactNode } from "react";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";
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
        "motion-card rounded-2xl transition duration-200",
        interactive && [
          "cursor-pointer hover:-translate-y-0.5 hover:shadow-glow",
          MOTION_INTERACTIVE_CLASS,
        ],
        className,
      )}
    >
      {children}
    </div>
  );
}
