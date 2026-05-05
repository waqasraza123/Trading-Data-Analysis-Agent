import { Badge } from "@/components/ui/Badge";
import { toneForDataQuality } from "@/lib/ui/statusStyles";

export function DataQualityBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Quality unavailable"} tone={toneForDataQuality(value)} />;
}
