import { Badge } from "@/components/status/badge";
import { diagnosticTone } from "@/lib/review/labels";

export function JournalReflectionBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value} tone={diagnosticTone(value)} />;
}
