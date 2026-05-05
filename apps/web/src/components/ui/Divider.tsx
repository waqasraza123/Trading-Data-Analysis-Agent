import { cn } from "@/lib/ui/cn";

type DividerProps = {
  className?: string;
};

export function Divider({ className }: DividerProps) {
  return <div className={cn("h-px w-full bg-gradient-to-r from-transparent via-[var(--border)] to-transparent", className)} />;
}
