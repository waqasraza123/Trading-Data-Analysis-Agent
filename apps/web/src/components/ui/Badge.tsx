import type { ReactNode } from "react";
import { uiLabel } from "@/lib/ui/labels";
import { statusToneClassName, type StatusTone } from "@/lib/ui/statusStyles";

export type BadgeProps = {
  value?: string | null;
  tone?: StatusTone;
  children?: ReactNode;
  className?: string;
};

export function Badge({ value, tone = "neutral", children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex min-h-7 max-w-full items-center rounded-md border px-2.5 py-1 text-xs font-medium leading-4 ${statusToneClassName[tone]} ${className}`}
    >
      <span className="truncate">{children ?? uiLabel(value)}</span>
    </span>
  );
}
