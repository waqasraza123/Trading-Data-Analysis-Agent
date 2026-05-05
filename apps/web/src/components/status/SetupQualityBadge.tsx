import { Badge } from "@/components/ui/Badge";
import { toneForSetupQuality } from "@/lib/ui/statusStyles";

export function SetupQualityBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Setup quality unavailable"} tone={toneForSetupQuality(value)} />;
}
