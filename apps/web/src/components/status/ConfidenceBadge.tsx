import { Badge } from "@/components/ui/Badge";
import { toneForConfidence } from "@/lib/ui/statusStyles";

export function ConfidenceBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value} tone={toneForConfidence(value)} />;
}
