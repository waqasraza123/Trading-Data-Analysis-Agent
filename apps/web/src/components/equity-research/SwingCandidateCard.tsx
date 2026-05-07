import Link from "next/link";
import { Badge } from "@/components/status/badge";
import {
  compactEquitySymbol,
  equityLabel,
  equityStatusTone,
  formatScore,
} from "@/lib/equity-research/labels";
import type { EquityResearchData, EquitySwingCandidate } from "@/lib/equity-research/types";

export function SwingCandidateCard({
  candidate,
  data,
}: {
  candidate: EquitySwingCandidate;
  data: EquityResearchData;
}) {
  return (
    <Link
      className="muted-surface block rounded-lg p-4 transition hover:border-[var(--accent)]"
      href={`/equity-research?workspaceId=${candidate.workspace_id}&scanRunId=${candidate.scan_run_id}&candidateId=${candidate.id}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-base font-semibold text-[var(--strong)]">
            {compactEquitySymbol(data.stockSymbols, candidate.symbol_id)}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            {equityLabel(candidate.setup_type)} · {candidate.timeframe}
          </p>
        </div>
        <Badge value={equityLabel(candidate.setup_quality_label)} tone={equityStatusTone(candidate.setup_quality_label)} />
      </div>
      <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <Metric label="Score" value={formatScore(candidate.setup_quality_score)} />
        <Metric label="Bias" value={equityLabel(candidate.directional_bias)} />
        <Metric label="Status" value={equityLabel(candidate.candidate_status)} />
      </div>
    </Link>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
