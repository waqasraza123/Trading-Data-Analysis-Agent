import { Badge } from "@/components/ui/Badge";
import { toneForPriority } from "@/lib/ui/statusStyles";

export function PriorityBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Priority unavailable"} tone={toneForPriority(value)} />;
}
