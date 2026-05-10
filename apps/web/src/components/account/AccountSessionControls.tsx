"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { revokeAuthSession, revokeOtherAuthSessions, type AuthSession } from "@/lib/api/account";

type PendingAction = `revoke-${string}` | `sign-out-${string}`;

export function AccountSessionControls({ session }: { session: AuthSession }) {
  const router = useRouter();
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const isActive = session.status === "active";

  async function revokeSession() {
    setPendingAction(`revoke-${session.id}`);
    setErrorMessage(null);
    const result = await revokeAuthSession(session.id);
    if (!result.ok) {
      setErrorMessage(result.error.message);
      setPendingAction(null);
      return;
    }
    router.refresh();
    setPendingAction(null);
  }

  async function signOutCurrentSession() {
    setPendingAction(`sign-out-${session.id}`);
    setErrorMessage(null);
    const response = await fetch("/api/auth/logout", { method: "POST" });
    if (!response.ok) {
      setErrorMessage("Unable to sign out this session");
      setPendingAction(null);
      return;
    }
    router.push("/login");
    router.refresh();
  }

  if (!isActive) {
    return <span className="text-xs text-[var(--text-muted)]">No action available</span>;
  }

  return (
    <div className="flex flex-col items-start gap-2">
      {session.current ? (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          loading={pendingAction === `sign-out-${session.id}`}
          onClick={signOutCurrentSession}
        >
          Sign out
        </Button>
      ) : (
        <Button
          type="button"
          size="sm"
          variant="danger"
          loading={pendingAction === `revoke-${session.id}`}
          onClick={revokeSession}
        >
          Revoke
        </Button>
      )}
      {errorMessage && <span className="text-xs font-medium text-[var(--danger)]">{errorMessage}</span>}
    </div>
  );
}

export function RevokeOtherSessionsButton({ disabled }: { disabled: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function revokeOtherSessions() {
    setPending(true);
    setMessage(null);
    const result = await revokeOtherAuthSessions();
    if (!result.ok) {
      setMessage(result.error.message);
      setPending(false);
      return;
    }
    setMessage(`${result.data.revoked_count} sessions revoked`);
    router.refresh();
    setPending(false);
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        type="button"
        variant="danger"
        loading={pending}
        disabled={disabled}
        onClick={revokeOtherSessions}
      >
        Revoke other sessions
      </Button>
      {message && <span className="text-xs font-medium text-[var(--text-muted)]">{message}</span>}
    </div>
  );
}
