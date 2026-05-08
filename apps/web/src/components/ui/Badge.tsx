import type { ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { uiLabel } from "@/lib/ui/labels";
import { statusDotClassName, statusToneClassName, type StatusTone } from "@/lib/ui/statusStyles";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";

export type BadgeProps = {
  value?: string | null;
  tone?: StatusTone;
  children?: ReactNode;
  className?: string;
  dot?: boolean;
  interactive?: boolean;
};

export function Badge({ value, tone = "neutral", children, className, dot = false, interactive = false }: BadgeProps) {
  return (
    <span
      className={cn(
        "motion-hover-lift inline-flex min-h-7 max-w-full items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold leading-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]",
        statusToneClassName[tone],
        interactive && MOTION_INTERACTIVE_CLASS,
        className,
      )}
    >
      {dot && <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", statusDotClassName[tone])} />}
      <span className="truncate">{children ?? uiLabel(value)}</span>
    </span>
  );
}
