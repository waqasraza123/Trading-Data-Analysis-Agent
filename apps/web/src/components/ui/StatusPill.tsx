import { Badge } from "./Badge";
import type { StatusTone } from "@/lib/ui/statusStyles";

type StatusPillProps = {
  label: string;
  value: string | number;
  tone?: StatusTone;
};

export function StatusPill({ label, value, tone = "neutral" }: StatusPillProps) {
  return (
    <div className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-3 py-2">
      <span className="text-xs font-medium uppercase text-slate-500">{label}</span>
      <Badge value={String(value)} tone={tone} />
    </div>
  );
}
