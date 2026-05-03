import { Badge } from "@/components/status/badge";
import type { TriageReason } from "@/lib/triage/types";

export function TriageReasonBadges({ reasons, limit = 4 }: { reasons: TriageReason[]; limit?: number }) {
  const visibleReasons = reasons.slice(0, limit);
  const hiddenCount = Math.max(0, reasons.length - visibleReasons.length);

  return (
    <div className="flex flex-wrap gap-2">
      {visibleReasons.map((reason) => (
        <Badge key={reason.label} value={reason.label} tone={reason.tone} />
      ))}
      {hiddenCount > 0 && <Badge value={`+${hiddenCount} context`} tone="neutral" />}
    </div>
  );
}
