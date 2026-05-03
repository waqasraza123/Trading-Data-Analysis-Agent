import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";

export function AvoidConditions({ data }: { data: DashboardData }) {
  const conditions = new Set<string>();
  if (!data.selectedSignal) {
    conditions.add("No directional signal");
  }
  if (data.selectedSignal?.signal.no_signal_reason) {
    conditions.add(data.selectedSignal.signal.no_signal_reason);
  }
  if (data.memorySnapshots.some((snapshot) => snapshot.freshness_label !== "fresh")) {
    conditions.add("Data stale");
  }
  if (data.memorySnapshots.some((snapshot) => snapshot.data_quality_label === "weak")) {
    conditions.add("Low data quality");
  }
  if (data.selectedSignal?.risk_notes.some((note) => note.severity === "high")) {
    conditions.add("Evidence conflict");
  }
  if (data.selectedOutcomes.some((outcome) => outcome.evaluation_status === "insufficient_future_data")) {
    conditions.add("Insufficient future data");
  }
  if (data.failures.length > 0) {
    conditions.add("Review recommended");
  }

  return (
    <Panel title="Avoid Conditions" eyebrow="Read-only guardrails">
      <div className="flex flex-wrap gap-2">
        {Array.from(conditions).length ? (
          Array.from(conditions).map((condition) => <Badge key={condition} value={condition} tone="warning" />)
        ) : (
          <Badge value="No blocking condition reported" tone="good" />
        )}
      </div>
    </Panel>
  );
}
