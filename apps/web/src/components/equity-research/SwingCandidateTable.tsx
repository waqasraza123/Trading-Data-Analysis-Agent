"use client";

import { useMemo, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import {
  compactEquitySymbol,
  equityCandidateStatusFilters,
  equityLabel,
  equityQualityFilters,
  equitySetupTypeFilters,
  equityStatusTone,
  formatScore,
} from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";
import { SwingCandidateCard } from "./SwingCandidateCard";

export function SwingCandidateTable({ data }: { data: EquityResearchData }) {
  const [setupType, setSetupType] = useState("all");
  const [candidateStatus, setCandidateStatus] = useState("all");
  const [qualityLabel, setQualityLabel] = useState("all");
  const filteredCandidates = useMemo(
    () =>
      data.candidates.filter(
        (candidate) =>
          (setupType === "all" || candidate.setup_type === setupType) &&
          (candidateStatus === "all" || candidate.candidate_status === candidateStatus) &&
          (qualityLabel === "all" || candidate.setup_quality_label === qualityLabel),
      ),
    [candidateStatus, data.candidates, qualityLabel, setupType],
  );

  return (
    <Panel
      title="Ranked swing setup candidates"
      eyebrow={data.selectedScanRun ? `Scan ${data.selectedScanRun.id.slice(0, 8)}` : "No scan selected"}
    >
      <div className="grid gap-3 md:grid-cols-3">
        <FilterSelect label="Setup type" options={equitySetupTypeFilters} value={setupType} onChange={setSetupType} />
        <FilterSelect
          label="Candidate status"
          options={equityCandidateStatusFilters}
          value={candidateStatus}
          onChange={setCandidateStatus}
        />
        <FilterSelect label="Setup quality" options={equityQualityFilters} value={qualityLabel} onChange={setQualityLabel} />
      </div>
      <div className="mt-4 hidden overflow-hidden rounded-lg border border-[var(--line)] xl:block">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-[var(--panel-muted)] text-xs uppercase tracking-[0.12em] text-slate-500">
            <tr>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Timeframe</th>
              <th className="px-4 py-3">Setup type</th>
              <th className="px-4 py-3">Bias</th>
              <th className="px-4 py-3">Quality</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Volume</th>
              <th className="px-4 py-3">Trend</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {filteredCandidates.map((candidate) => (
              <tr key={candidate.id}>
                <td className="px-4 py-3 font-semibold text-[var(--strong)]">
                  {compactEquitySymbol(data.stockSymbols, candidate.symbol_id)}
                </td>
                <td className="px-4 py-3 text-slate-500">{candidate.timeframe}</td>
                <td className="px-4 py-3 text-slate-500">{equityLabel(candidate.setup_type)}</td>
                <td className="px-4 py-3 text-slate-500">{equityLabel(candidate.directional_bias)}</td>
                <td className="px-4 py-3">
                  <Badge
                    value={equityLabel(candidate.setup_quality_label)}
                    tone={equityStatusTone(candidate.setup_quality_label)}
                  />
                </td>
                <td className="px-4 py-3 font-semibold text-[var(--strong)]">
                  {formatScore(candidate.setup_quality_score)}
                </td>
                <td className="px-4 py-3 text-slate-500">{formatScore(candidate.volume_score)}</td>
                <td className="px-4 py-3 text-slate-500">{formatScore(candidate.trend_quality_score)}</td>
                <td className="px-4 py-3 text-slate-500">{equityLabel(candidate.candidate_status)}</td>
              </tr>
            ))}
            {filteredCandidates.length === 0 && (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={9}>
                  No candidates match the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="mt-4 grid gap-3 xl:hidden">
        {filteredCandidates.map((candidate) => (
          <SwingCandidateCard key={candidate.id} candidate={candidate} data={data} />
        ))}
        {filteredCandidates.length === 0 && (
          <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
            No candidates match the selected filters.
          </div>
        )}
      </div>
    </Panel>
  );
}

function FilterSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-semibold text-[var(--strong)]">
      {label}
      <select
        className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option === "all" ? "All" : equityLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
