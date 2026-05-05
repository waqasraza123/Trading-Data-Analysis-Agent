import { Badge } from "@/components/ui/Badge";
import { toneForWorkerStatus } from "@/lib/ui/statusStyles";

export function WorkerStatusBadge({ value }: { value: string | null | undefined }) {
  return <Badge value={value || "Worker status unavailable"} tone={toneForWorkerStatus(value)} />;
}
