import { Badge } from "@/components/ui/Badge";
import { toneForReadiness } from "@/lib/ui/statusStyles";

export function ReadinessBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Readiness unavailable"} tone={toneForReadiness(value)} />;
}
