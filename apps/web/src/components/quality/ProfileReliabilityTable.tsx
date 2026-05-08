import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function ProfileReliabilityTable({ data }: { data: QualityScoreboardData }) {
  if (data.profileRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Strategy profile reliability" eyebrow="Observed behavior by profile">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Strategy profile</th>
              <th className="px-3 py-2">Sample size</th>
              <th className="px-3 py-2">Continuation rate</th>
              <th className="px-3 py-2">Reversal rate</th>
              <th className="px-3 py-2">No follow-through rate</th>
              <th className="px-3 py-2">Confidence alignment</th>
              <th className="px-3 py-2">Diagnostic label</th>
              <th className="px-3 py-2">Recommendation status</th>
            </tr>
          </thead>
          <tbody>
            {data.profileRows.map((row, index) => (
              <AnimatedListItem
                as="tr"
                key={row.key}
                className={`${motionRevealPresetClass()} border-t border-[var(--line)] align-top`}
                style={motionRevealDensityStyle(index, "compact")}
              >
                <td className="px-3 py-3 font-medium text-[var(--strong)]">
                  {qualityLabel(row.key)}
                  <p className="mt-1 max-w-xs text-xs font-normal leading-5 text-slate-500">{row.summary}</p>
                </td>
                <td className="px-3 py-3">{row.sampleSize}</td>
                <td className="px-3 py-3">{formatPercent(row.continuationRate)}</td>
                <td className="px-3 py-3">{formatPercent(row.reversalRate)}</td>
                <td className="px-3 py-3">{formatPercent(row.noFollowThroughRate)}</td>
                <td className="px-3 py-3">{formatPercent(row.confidenceAlignment)}</td>
                <td className="px-3 py-3"><Badge value={qualityLabel(row.diagnosticLabel)} tone={qualityTone(row.diagnosticLabel)} /></td>
                <td className="px-3 py-3">{row.recommendationStatus ? <Badge value={row.recommendationStatus} tone="info" /> : <span className="text-slate-500">Not returned</span>}</td>
              </AnimatedListItem>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
