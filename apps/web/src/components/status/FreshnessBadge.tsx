import { Badge } from "@/components/ui/Badge";
import { toneForFreshness } from "@/lib/ui/statusStyles";

export function FreshnessBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Freshness unavailable"} tone={toneForFreshness(value)} />;
}
