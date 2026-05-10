"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Surface } from "@/components/ui/Surface";
import { loginWithPassword, registerWithPassword } from "@/lib/api/auth";

type AuthMode = "login" | "register";

type AuthCardProps = {
  mode: AuthMode;
};

export function AuthCard({ mode }: AuthCardProps) {
  const router = useRouter();
  const [workspaceName, setWorkspaceName] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setErrorMessage(null);
    const result = isRegister
      ? await registerWithPassword({ workspaceName, name, email, password })
      : await loginWithPassword(email, password);
    setLoading(false);
    if (!result.ok) {
      setErrorMessage(result.message || "Authentication failed");
      return;
    }
    router.push("/command-center");
    router.refresh();
  }

  return (
    <Surface className="w-full max-w-md p-6 shadow-panel">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent)]">
          Operator access
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-[var(--strong)]">
          {isRegister ? "Create your workspace" : "Sign in to the cockpit"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">
          Use a workspace account backed by the configured Neon Postgres database.
        </p>
      </div>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        {isRegister && (
          <>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
                Workspace
              </span>
              <input
                className="premium-control mt-2 w-full px-3 py-2.5 text-sm text-[var(--strong)] outline-none"
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
                autoComplete="organization"
                required
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
                Name
              </span>
              <input
                className="premium-control mt-2 w-full px-3 py-2.5 text-sm text-[var(--strong)] outline-none"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                required
              />
            </label>
          </>
        )}
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
            Email
          </span>
          <input
            className="premium-control mt-2 w-full px-3 py-2.5 text-sm text-[var(--strong)] outline-none"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--text-muted)]">
            Password
          </span>
          <input
            className="premium-control mt-2 w-full px-3 py-2.5 text-sm text-[var(--strong)] outline-none"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            minLength={isRegister ? 12 : 1}
            required
          />
        </label>
        {errorMessage && (
          <div className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-3 py-2 text-sm text-[var(--danger)]">
            {errorMessage}
          </div>
        )}
        <Button className="w-full" variant="primary" size="lg" loading={loading} type="submit">
          {isRegister ? "Create workspace" : "Sign in"}
        </Button>
      </form>
      <div className="mt-5 text-sm text-[var(--text-muted)]">
        {isRegister ? (
          <span>
            Already have access?{" "}
            <Link className="font-semibold text-[var(--accent-strong)]" href="/login">
              Sign in
            </Link>
          </span>
        ) : (
          <span>
            Need a workspace?{" "}
            <Link className="font-semibold text-[var(--accent-strong)]" href="/register">
              Create one
            </Link>
          </span>
        )}
      </div>
    </Surface>
  );
}
