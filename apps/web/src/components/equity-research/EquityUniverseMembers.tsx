"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { addEquityUniverseMember, removeEquityUniverseMember } from "@/lib/api/equityResearch";
import { equitySymbolLabel } from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityUniverseMembers({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const firstSymbolId = data.stockSymbols[0]?.id || "";
  const [symbolId, setSymbolId] = useState(firstSymbolId);
  const [averageVolume, setAverageVolume] = useState("");
  const [sector, setSector] = useState("");
  const [exchange, setExchange] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  async function submitMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.selectedUniverse) {
      setMessage("Create or select a universe first.");
      return;
    }
    if (!symbolId) {
      setMessage("Select a stock symbol.");
      return;
    }
    setPending("add");
    setMessage(null);
    const result = await addEquityUniverseMember(data.selectedUniverse.id, {
      symbol_id: symbolId,
      average_volume: averageVolume ? Number(averageVolume) : undefined,
      sector: sector || undefined,
      exchange: exchange || undefined,
    });
    setPending(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setAverageVolume("");
    setSector("");
    setExchange("");
    router.refresh();
  }

  async function removeMember(memberId: string) {
    if (!data.selectedUniverse) {
      return;
    }
    setPending(memberId);
    setMessage(null);
    const result = await removeEquityUniverseMember(data.selectedUniverse.id, memberId);
    setPending(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <Panel title="Universe members" eyebrow={data.selectedUniverse?.name || "No universe selected"}>
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <form className="grid gap-3 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 md:grid-cols-4" onSubmit={submitMember}>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Symbol
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={symbolId} onChange={(event) => setSymbolId(event.target.value)}>
            {data.stockSymbols.length === 0 && <option value="">No stock symbols</option>}
            {data.stockSymbols.map((symbol) => (
              <option key={symbol.id} value={symbol.id}>{symbol.symbol} · {symbol.display_name}</option>
            ))}
          </select>
        </label>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Average volume
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" inputMode="numeric" value={averageVolume} onChange={(event) => setAverageVolume(event.target.value)} />
        </label>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Sector
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={sector} onChange={(event) => setSector(event.target.value)} />
        </label>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Exchange
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={exchange} onChange={(event) => setExchange(event.target.value)} />
        </label>
        <button className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60 md:col-span-4" disabled={!data.selectedUniverse || !symbolId || pending === "add"} type="submit">
          {pending === "add" ? "Adding" : "Add symbol"}
        </button>
      </form>
      <div className="mt-4 overflow-hidden rounded-lg border border-[var(--line)]">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-[var(--panel-muted)] text-xs uppercase tracking-[0.12em] text-slate-500">
            <tr>
              <th className="px-4 py-3">Symbol</th>
              <th className="px-4 py-3">Sector</th>
              <th className="px-4 py-3">Exchange</th>
              <th className="px-4 py-3">Average volume</th>
              <th className="px-4 py-3">State</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--line)]">
            {data.selectedUniverseMembers.map((member) => (
              <tr key={member.id}>
                <td className="px-4 py-3 font-semibold text-[var(--strong)]">{equitySymbolLabel(data.stockSymbols, member.symbol_id)}</td>
                <td className="px-4 py-3 text-slate-500">{member.sector || "Not set"}</td>
                <td className="px-4 py-3 text-slate-500">{member.exchange || "Not set"}</td>
                <td className="px-4 py-3 text-slate-500">{member.average_volume || "Unknown"}</td>
                <td className="px-4 py-3">
                  <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-semibold disabled:opacity-50" disabled={pending === member.id} type="button" onClick={() => removeMember(member.id)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {data.selectedUniverseMembers.length === 0 && (
              <tr>
                <td className="px-4 py-5 text-slate-500" colSpan={5}>No active members in this universe.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
