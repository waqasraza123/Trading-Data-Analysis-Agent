"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function UserStep({ mutation, onComplete }: SetupWizardStepProps) {
  const [email, setEmail] = useState("operator@example.test");
  const [name, setName] = useState("Market Operator");
  const [role, setRole] = useState("analyst");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onComplete("user", { mode: "create", email, name, role });
  }

  return (
    <Panel title="Operator" eyebrow="Workspace user">
      <form className="grid gap-4 md:grid-cols-3" onSubmit={submit}>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} />
        </label>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Email
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={email} maxLength={320} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Role
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="analyst">Analyst</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <div className="md:col-span-3">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            Save operator
          </button>
        </div>
      </form>
    </Panel>
  );
}
