"use client";

import { useEffect, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/Button";
import { getCurrentIdentity, logout, type CurrentIdentity } from "@/lib/api/auth";

export function AuthStatus() {
  const [identity, setIdentity] = useState<CurrentIdentity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getCurrentIdentity().then((result) => {
      if (!active) {
        return;
      }
      setIdentity(result.ok ? result.data : null);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    await logout();
    setIdentity(null);
    window.location.href = "/login";
  }

  if (loading) {
    return <div className="h-9 w-28 rounded-xl bg-[var(--surface-muted)]" />;
  }

  if (!identity?.authenticated) {
    return <ButtonLink href="/login" size="sm" variant="primary">Sign in</ButtonLink>;
  }

  return (
    <div className="flex items-center gap-2">
      <div className="hidden min-w-0 text-right xl:block">
        <p className="truncate text-xs font-semibold text-[var(--strong)]">
          {identity.user?.name || identity.user?.email || "Authenticated"}
        </p>
        <p className="truncate text-xs text-[var(--text-muted)]">
          {identity.workspace?.name || "Workspace"}
        </p>
      </div>
      <Button size="sm" variant="quiet" onClick={handleLogout}>Sign out</Button>
    </div>
  );
}
