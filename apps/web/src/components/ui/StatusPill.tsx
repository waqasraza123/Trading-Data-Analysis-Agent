import { Badge } from "./Badge";
import type { StatusTone } from "@/lib/ui/statusStyles";

type StatusPillProps = {
  label: string;
  value: string | number;
  tone?: StatusTone;
};

export function StatusPill({ label, value, tone = "neutral" }: StatusPillProps) {
  return (
    <div className="premium-control inline-flex min-h-10 items-center gap-2 rounded-full px-3 py-2">
      <span className="text-xs font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]">{label}</span>
      <Badge value={String(value)} tone={tone} dot />
    </div>
  );
}
