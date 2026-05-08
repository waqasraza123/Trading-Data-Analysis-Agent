"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { listWorkspaces } from "@/lib/api/market";
import type { Workspace } from "@/lib/api/types";
import {
  readSelectedWorkspaceId,
  resolveSelectedWorkspace,
  workspaceScopedHref,
  writeSelectedWorkspaceId,
} from "@/lib/workspace/selectedWorkspace";
import { WorkspaceMissingState } from "./WorkspaceMissingState";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";

type WorkspaceSelectorProps = {
  workspaceId?: string | null;
  workspaceName?: string | null;
};

export function WorkspaceSelector({ workspaceId, workspaceName }: WorkspaceSelectorProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [workspaces, setWorkspaces] = useState<Workspace[]>(
    workspaceId && workspaceName
      ? [{ id: workspaceId, name: workspaceName, created_at: "", updated_at: "" }]
      : [],
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    void listWorkspaces().then((result) => {
      if (result.ok) {
        setWorkspaces(result.data);
      }
      setLoading(false);
    });
  }, []);

  const storedId = typeof window === "undefined" ? null : readSelectedWorkspaceId();
  const selected = useMemo(
    () => resolveSelectedWorkspace(workspaces, workspaceId || searchParams.get("workspaceId"), storedId),
    [workspaces, workspaceId, searchParams, storedId],
  );

  function selectWorkspace(nextWorkspaceId: string) {
    writeSelectedWorkspaceId(nextWorkspaceId || null);
    const params = new URLSearchParams(searchParams.toString());
    if (nextWorkspaceId) {
      params.set("workspaceId", nextWorkspaceId);
    } else {
      params.delete("workspaceId");
    }
    const query = params.toString();
    window.location.href = workspaceScopedHref(`${pathname}${query ? `?${query}` : ""}`, nextWorkspaceId || null);
  }

  if (!loading && workspaces.length === 0) {
    return <WorkspaceMissingState />;
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-3">
      <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]" htmlFor="workspace-selector">
        Workspace
      </label>
      <select
        id="workspace-selector"
        className={`mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-semibold text-[var(--strong)] transition ${MOTION_INTERACTIVE_CLASS}`}
        value={selected?.id || ""}
        onChange={(event) => selectWorkspace(event.target.value)}
      >
        {workspaces.length === 0 && <option value="">Loading workspaces</option>}
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.name}
          </option>
        ))}
      </select>
      <p className="mt-2 truncate text-xs text-[var(--text-muted)]">
        {selected ? "Selected workspace context" : "Workspace context needed"}
      </p>
    </div>
  );
}
