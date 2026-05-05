import { Badge } from "@/components/ui/Badge";
import { toneForOutcome } from "@/lib/ui/statusStyles";

export function OutcomeLabelBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Outcome unavailable"} tone={toneForOutcome(value)} />;
}
