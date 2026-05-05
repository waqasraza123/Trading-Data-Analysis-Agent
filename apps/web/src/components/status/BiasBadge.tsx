import { Badge } from "@/components/ui/Badge";
import { toneForBias } from "@/lib/ui/statusStyles";

export function BiasBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "No directional signal"} tone={toneForBias(value)} />;
}
