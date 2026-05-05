"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { runProductReadiness } from "@/lib/api/productReadiness";
import type { UUID } from "@/lib/api/types";

export function ReadinessRunButton({ workspaceId }: { workspaceId?: UUID | null }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runChecklist() {
    setPending(true);
    setMessage(null);
    const result = await runProductReadiness(workspaceId || null);
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    if (workspaceId) {
      params.set("workspaceId", workspaceId);
    }
    params.set("runId", result.data.id);
    router.push(`/readiness?${params.toString()}`);
    router.refresh();
  }

  return (
    <div className="space-y-2">
      <button
        className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending}
        type="button"
        onClick={runChecklist}
      >
        {pending ? "Running checklist" : "Run readiness check"}
      </button>
      {message && <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
    </div>
  );
}
