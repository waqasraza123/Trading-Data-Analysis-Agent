import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { WorkspaceBrief } from "@/lib/brief/types";

export function BriefErrorState({ brief }: { brief: WorkspaceBrief }) {
  if (!brief.backendUnavailable) {
    return null;
  }

  return (
    <Panel title="Backend unavailable" eyebrow="Brief composition">
      <div className="flex flex-wrap gap-2">
        <Badge value="Backend unavailable" tone="warning" />
        <Badge value={brief.apiBaseUrl} tone="info" />
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
        The brief could not reach the backend reliably. Any section below is limited to responses that were already returned.
      </p>
    </Panel>
  );
}
