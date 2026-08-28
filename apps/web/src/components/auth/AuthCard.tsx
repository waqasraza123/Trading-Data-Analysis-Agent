"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/Button";
import { loginWithPassword, registerWithPassword } from "@/lib/api/auth";

type AuthMode = "login" | "register";

type AuthCardProps = {
  mode: AuthMode;
  nextPath?: string;
};

export function AuthCard({ mode, nextPath }: AuthCardProps) {
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
    router.push(isRegister ? "/onboarding" : safeNextPath(nextPath));
    router.refresh();
  }

  return (
    <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#090f1b]/95 p-6 text-slate-100 shadow-[0_28px_100px_rgba(0,0,0,0.45)] backdrop-blur-xl sm:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent)]">
          Starter workspace
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-white">
          {isRegister ? "Create your workspace" : "Welcome back"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          {isRegister
            ? "Start with an isolated Neon-backed workspace and an administrator account."
            : "Continue to your private trading-intelligence workspace."}
        </p>
      </div>
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        {isRegister && (
          <>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                Workspace
              </span>
              <input
                className="mt-2 w-full rounded-lg border border-white/10 bg-white/[0.045] px-3 py-2.5 text-sm text-white outline-none transition focus:border-teal-300/60 focus:ring-4 focus:ring-teal-300/10"
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
                autoComplete="organization"
                required
              />
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
                Name
              </span>
              <input
                className="mt-2 w-full rounded-lg border border-white/10 bg-white/[0.045] px-3 py-2.5 text-sm text-white outline-none transition focus:border-teal-300/60 focus:ring-4 focus:ring-teal-300/10"
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                required
              />
            </label>
          </>
        )}
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Email
          </span>
          <input
            className="mt-2 w-full rounded-lg border border-white/10 bg-white/[0.045] px-3 py-2.5 text-sm text-white outline-none transition focus:border-teal-300/60 focus:ring-4 focus:ring-teal-300/10"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            required
          />
        </label>
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            Password
          </span>
          <input
            className="mt-2 w-full rounded-lg border border-white/10 bg-white/[0.045] px-3 py-2.5 text-sm text-white outline-none transition focus:border-teal-300/60 focus:ring-4 focus:ring-teal-300/10"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete={isRegister ? "new-password" : "current-password"}
            minLength={isRegister ? 12 : 1}
            required
          />
        </label>
        {isRegister && (
          <p className="text-xs leading-5 text-slate-500">
            Use at least 12 characters. Passwords are hashed before they are stored.
          </p>
        )}
        {errorMessage && (
          <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {errorMessage}
          </div>
        )}
        <Button className="w-full" variant="primary" size="lg" loading={loading} type="submit">
          {isRegister ? "Create workspace" : "Sign in"}
        </Button>
      </form>
      <div className="mt-5 text-sm text-slate-500">
        {isRegister ? (
          <span>
            Already have access?{" "}
            <Link className="font-semibold text-teal-300" href="/login">
              Sign in
            </Link>
          </span>
        ) : (
          <span>
            Need a workspace?{" "}
            <Link className="font-semibold text-teal-300" href="/register">
              Create one
            </Link>
          </span>
        )}
      </div>
    </div>
  );
}

function safeNextPath(value: string | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/command-center";
  }
  return value;
}
