import { Badge } from "@/components/status/badge";
import { providerHealthReadinessLabel, providerHealthTone } from "@/lib/provider-health/labels";
import type { ProviderHealthSnapshot } from "@/lib/provider-health/types";

type DataReadinessBadgeProps = {
  snapshot: ProviderHealthSnapshot;
};

export function DataReadinessBadge({ snapshot }: DataReadinessBadgeProps) {
  const label = providerHealthReadinessLabel(snapshot);
  return <Badge value={label} tone={providerHealthTone(snapshot.status)} />;
}
