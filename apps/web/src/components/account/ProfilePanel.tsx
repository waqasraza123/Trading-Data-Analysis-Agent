"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { updateProfile } from "@/lib/api/account";

export function ProfilePanel({ name, email }: { name: string; email: string }) {
  const router = useRouter();
  const [profileName, setProfileName] = useState(name);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage(null);
    setErrorMessage(null);
    const result = await updateProfile(profileName);
    if (!result.ok) {
      setErrorMessage(result.error.message);
      setPending(false);
      return;
    }
    setProfileName(result.data.user?.name || profileName);
    setMessage("Profile updated");
    setPending(false);
    router.refresh();
  }

  return (
    <form className="grid gap-4" onSubmit={submitProfile}>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Name</span>
        <input
          className="premium-control min-h-10 rounded-md px-3 py-2 text-sm text-[var(--strong)] outline-none"
          value={profileName}
          minLength={1}
          maxLength={160}
          required
          autoComplete="name"
          onChange={(event) => setProfileName(event.target.value)}
        />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">Email</span>
        <input
          className="min-h-10 rounded-md border border-[var(--line)] bg-[var(--panel-muted)] px-3 py-2 text-sm text-[var(--text-muted)]"
          value={email}
          disabled
        />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" loading={pending} disabled={profileName.trim() === name}>
          Save profile
        </Button>
        {message && <span className="text-sm font-medium text-[var(--success)]">{message}</span>}
        {errorMessage && <span className="text-sm font-medium text-[var(--danger)]">{errorMessage}</span>}
      </div>
    </form>
  );
}
