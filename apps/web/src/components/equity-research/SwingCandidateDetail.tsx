import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import {
  compactEquitySymbol,
  equityLabel,
  equityStatusTone,
  formatScore,
  jsonValueLabel,
} from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function SwingCandidateDetail({ data }: { data: EquityResearchData }) {
  const candidate = data.selectedCandidate;
  if (!candidate) {
    return (
      <Panel title="Candidate detail" eyebrow="No candidate selected">
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
          Run or select a swing scan to review candidate evidence and context.
        </div>
      </Panel>
    );
  }

  return (
    <Panel
      title={`${compactEquitySymbol(data.stockSymbols, candidate.symbol_id)} candidate detail`}
      eyebrow={`${equityLabel(candidate.setup_type)} · ${candidate.timeframe}`}
    >
      <div className="flex flex-wrap gap-2">
        <Badge value={equityLabel(candidate.setup_quality_label)} tone={equityStatusTone(candidate.setup_quality_label)} />
        <Badge value={equityLabel(candidate.candidate_status)} tone={equityStatusTone(candidate.candidate_status)} />
        <Badge value={equityLabel(candidate.directional_bias)} tone="info" />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Setup score", formatScore(candidate.setup_quality_score)],
          ["Liquidity", formatScore(candidate.liquidity_score)],
          ["Volume", formatScore(candidate.volume_score)],
          ["Trend quality", formatScore(candidate.trend_quality_score)],
          ["Pullback quality", formatScore(candidate.pullback_quality_score)],
          ["Relative strength", formatScore(candidate.relative_strength_score)],
          ["Momentum", formatScore(candidate.momentum_score)],
          ["Volatility", formatScore(candidate.volatility_score)],
        ].map(([label, value], index) => (
          <AnimatedListItem
            as="article"
            key={`${label}-${value}`}
            className={cn(
              "rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3",
              motionCardClass,
              motionRevealPresetClass("scale-subtle"),
            )}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <Metric label={label} value={value} />
          </AnimatedListItem>
        ))}
      </div>
      <div className="mt-5 grid gap-4 xl:grid-cols-2">
        <ContextList title="Evidence" items={candidate.evidence_json} emptyLabel="No deterministic evidence stored." />
        <ContextList title="Review notes" items={candidate.risk_notes_json} emptyLabel="No review notes stored." />
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        {candidate.signal_id && (
          <Link
            className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)]"
            href={`/signals/${candidate.signal_id}?workspaceId=${candidate.workspace_id}`}
          >
            Open linked signal
          </Link>
        )}
        {candidate.setup_context_id && (
          <div className="rounded-md border border-[var(--line)] px-3 py-2 text-sm text-slate-500">
            Setup context {candidate.setup_context_id.slice(0, 8)}
          </div>
        )}
        {candidate.analysis_run_id && (
          <div className="rounded-md border border-[var(--line)] px-3 py-2 text-sm text-slate-500">
            Analysis run {candidate.analysis_run_id.slice(0, 8)}
          </div>
        )}
      </div>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}

function ContextList({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: Record<string, unknown>[];
  emptyLabel: string;
}) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
      <h3 className="text-sm font-semibold text-[var(--strong)]">{title}</h3>
      <div className="mt-3 grid gap-3">
        {items.map((item, index) => (
          <AnimatedListItem
            as="article"
            key={`${title}-${index}`}
            className={cn(
              "rounded-md bg-[var(--panel)] p-3",
              motionCardClass,
              motionRevealPresetClass("scale-subtle"),
            )}
            style={motionRevealDensityStyle(index, "compact")}
          >
            {Object.entries(item).map(([key, value]) => (
              <p key={key} className="mt-1 first:mt-0">
                <span className="font-semibold text-[var(--strong)]">{equityLabel(key)}:</span>{" "}
                <span className="text-slate-500">{jsonValueLabel(value)}</span>
              </p>
            ))}
          </AnimatedListItem>
        ))}
        {items.length === 0 && <p className="text-sm text-slate-500">{emptyLabel}</p>}
      </div>
    </div>
  );
}
