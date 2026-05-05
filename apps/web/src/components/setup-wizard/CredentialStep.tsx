"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function CredentialStep({ initialData, mutation, onComplete, onSkip }: SetupWizardStepProps) {
  const [mode, setMode] = useState<"none" | "select" | "create">("none");
  const [credentialRefId, setCredentialRefId] = useState(initialData.providerCredentialRefs[0]?.id || "");
  const [name, setName] = useState("Provider credential reference");
  const [provider, setProvider] = useState("mock");
  const [credentialType, setCredentialType] = useState("none_required");
  const [secretRef, setSecretRef] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "none") {
      await onSkip("credential_reference");
      return;
    }
    await onComplete(
      "credential_reference",
      mode === "select"
        ? { mode, credential_ref_id: credentialRefId }
        : {
            mode,
            name,
            provider,
            credential_type: credentialType,
            secret_ref: secretRef || undefined,
            public_metadata_json: { configuredFrom: "workspace_setup" },
          },
    );
  }

  return (
    <Panel title="Credential reference" eyebrow="Optional provider pointer">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Mode
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={mode} onChange={(event) => setMode(event.target.value as "none" | "select" | "create")}>
            <option value="none">No credential required</option>
            <option value="select">Select reference</option>
            <option value="create">Create reference</option>
          </select>
        </label>
        {mode === "select" && (
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Credential reference
            <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={credentialRefId} onChange={(event) => setCredentialRefId(event.target.value)}>
              {initialData.providerCredentialRefs.map((credential) => (
                <option key={credential.id} value={credential.id}>{credential.name} · {credential.provider}</option>
              ))}
            </select>
          </label>
        )}
        {mode === "create" && (
          <>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Name
              <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Provider
              <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={provider} onChange={(event) => setProvider(event.target.value)} />
            </label>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Credential type
              <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={credentialType} onChange={(event) => setCredentialType(event.target.value)}>
                <option value="none_required">None required</option>
                <option value="api_key">API key reference</option>
                <option value="bearer_token">Bearer token reference</option>
                <option value="oauth">OAuth reference</option>
              </select>
            </label>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Secret reference
              <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" placeholder="vault/provider/path" value={secretRef} onChange={(event) => setSecretRef(event.target.value)} />
            </label>
          </>
        )}
        <div className="md:col-span-2">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            {mode === "none" ? "Skip credential" : "Save credential reference"}
          </button>
        </div>
      </form>
    </Panel>
  );
}
