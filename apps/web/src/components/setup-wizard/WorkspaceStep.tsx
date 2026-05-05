"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function WorkspaceStep({ initialData, mutation, onComplete, onLocalSelectionChange }: SetupWizardStepProps) {
  const [mode, setMode] = useState<"create" | "select">(initialData.workspaces.length ? "select" : "create");
  const [workspaceId, setWorkspaceId] = useState(initialData.selectedWorkspaceId || initialData.workspaces[0]?.id || "");
  const [name, setName] = useState("Market Intelligence Workspace");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onComplete("workspace", mode === "select" ? { mode, workspace_id: workspaceId } : { mode, name });
    onLocalSelectionChange({ workspaceId: mode === "select" ? workspaceId : null });
  }

  return (
    <Panel title="Workspace" eyebrow="Create or select">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Mode
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={mode} onChange={(event) => setMode(event.target.value as "create" | "select")}>
            <option value="select">Select existing</option>
            <option value="create">Create new</option>
          </select>
        </label>
        {mode === "select" ? (
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Workspace
            <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)}>
              {initialData.workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
              ))}
            </select>
          </label>
        ) : (
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Workspace name
            <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} maxLength={120} onChange={(event) => setName(event.target.value)} />
          </label>
        )}
        <div className="md:col-span-2">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            Save workspace
          </button>
        </div>
      </form>
    </Panel>
  );
}
