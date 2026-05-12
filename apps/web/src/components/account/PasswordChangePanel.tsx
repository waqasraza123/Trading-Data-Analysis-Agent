"use client";

import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { changePassword } from "@/lib/api/account";

type PasswordChangeState = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  revokeOtherSessions: boolean;
};

const initialState: PasswordChangeState = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
  revokeOtherSessions: true,
};

export function PasswordChangePanel() {
  const [state, setState] = useState<PasswordChangeState>(initialState);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function submitPasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setErrorMessage(null);
    if (state.newPassword !== state.confirmPassword) {
      setErrorMessage("New password confirmation does not match");
      return;
    }
    setPending(true);
    const result = await changePassword({
      currentPassword: state.currentPassword,
      newPassword: state.newPassword,
      revokeOtherSessions: state.revokeOtherSessions,
    });
    if (!result.ok) {
      setErrorMessage(result.error.message);
      setPending(false);
      return;
    }
    setState(initialState);
    setMessage(
      state.revokeOtherSessions
        ? `Password changed. ${result.data.revoked_session_count} other sessions revoked.`
        : "Password changed.",
    );
    setPending(false);
  }

  return (
    <form className="grid gap-4" onSubmit={submitPasswordChange}>
      <PasswordField
        label="Current password"
        value={state.currentPassword}
        onChange={(currentPassword) => setState((current) => ({ ...current, currentPassword }))}
      />
      <PasswordField
        label="New password"
        value={state.newPassword}
        onChange={(newPassword) => setState((current) => ({ ...current, newPassword }))}
      />
      <PasswordField
        label="Confirm new password"
        value={state.confirmPassword}
        onChange={(confirmPassword) => setState((current) => ({ ...current, confirmPassword }))}
      />
      <label className="flex items-start gap-3 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3 text-sm">
        <input
          type="checkbox"
          className="mt-1"
          checked={state.revokeOtherSessions}
          onChange={(event) =>
            setState((current) => ({
              ...current,
              revokeOtherSessions: event.target.checked,
            }))
          }
        />
        <span>
          <span className="block font-medium text-[var(--strong)]">Revoke other active sessions</span>
          <span className="mt-1 block text-xs leading-5 text-[var(--text-muted)]">
            Keep this browser signed in and invalidate other first-party password sessions.
          </span>
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" loading={pending}>
          Change password
        </Button>
        {message && <span className="text-sm font-medium text-[var(--success)]">{message}</span>}
        {errorMessage && <span className="text-sm font-medium text-[var(--danger)]">{errorMessage}</span>}
      </div>
    </form>
  );
}

function PasswordField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</span>
      <input
        className="min-h-10 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm text-[var(--strong)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)]"
        type="password"
        value={value}
        minLength={label === "Current password" ? 1 : 12}
        maxLength={256}
        required
        autoComplete={label === "Current password" ? "current-password" : "new-password"}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
