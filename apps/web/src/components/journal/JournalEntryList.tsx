"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { archiveJournalEntry } from "@/lib/api/journal";
import type { JournalEntry } from "@/lib/api/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { shortIdentifier } from "@/lib/formatting/labels";
import { reviewLabel } from "@/lib/review/labels";
import { JournalReflectionBadge } from "./JournalReflectionBadge";
import { JournalEmptyState } from "./JournalEmptyState";

export function JournalEntryList({ entries, workspaceId }: { entries: JournalEntry[]; workspaceId: string | null | undefined }) {
  const router = useRouter();
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function archiveEntry(entryId: string) {
    setPendingId(entryId);
    setMessage(null);
    const result = await archiveJournalEntry(entryId);
    setPendingId(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  if (entries.length === 0) {
    return <JournalEmptyState />;
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Journal entries</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Recent reflection notes</h2>
        </div>
        {message && <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      </div>
      <div className="space-y-3">
        {entries.map((entry) => (
          <article key={entry.id} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{entry.title}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  {reviewLabel(entry.decision_type)} · {entry.user_bias ? reviewLabel(entry.user_bias) : "Bias not specified"} · {formatDateTime(entry.created_at)}
                </p>
              </div>
              <JournalReflectionBadge value={entry.status} />
            </div>
            <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{entry.user_notes}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              {entry.signal_id && <span>Signal {shortIdentifier(entry.signal_id)}</span>}
              {entry.setup_context_id && <span>Setup {shortIdentifier(entry.setup_context_id)}</span>}
              {entry.tags.map((tag) => (
                <span key={tag} className="rounded-md border border-[var(--line)] px-2 py-1">{tag}</span>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white" href={entryHref(entry.id, workspaceId)}>
                Open
              </Link>
              {entry.signal_id && (
                <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800" href={`/signals/${entry.signal_id}`}>
                  Signal detail
                </Link>
              )}
              {entry.status !== "archived" && (
                <button
                  className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-slate-800"
                  type="button"
                  disabled={pendingId === entry.id}
                  onClick={() => archiveEntry(entry.id)}
                >
                  Archive
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function entryHref(entryId: string, workspaceId: string | null | undefined): string {
  if (!workspaceId) {
    return `/journal/${entryId}`;
  }
  return `/journal/${entryId}?workspaceId=${workspaceId}`;
}
