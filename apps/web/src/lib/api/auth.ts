import { apiGet } from "./client";
import type { ApiResult, UUID } from "./types";

export type AuthUser = {
  id: UUID;
  workspace_id: UUID;
  email: string;
  name: string;
  role: string;
};

export type AuthWorkspace = {
  id: UUID;
  name: string;
};

export type CurrentIdentity = {
  authenticated: boolean;
  source: string | null;
  provider: string | null;
  provider_subject: string | null;
  user: AuthUser | null;
  workspace: AuthWorkspace | null;
  permissions: string[];
  scopes: string[];
  admin: boolean;
};

export type AuthSession = {
  access_token: string;
  token_type: string;
  expires_at: string;
  identity: CurrentIdentity;
};

export type AuthFormResult = {
  ok: boolean;
  message?: string;
  session?: AuthSession;
};

export async function getCurrentIdentity(): Promise<ApiResult<CurrentIdentity>> {
  return apiGet<CurrentIdentity>("/auth/me", { timeoutMs: 5000 });
}

export async function loginWithPassword(email: string, password: string): Promise<AuthFormResult> {
  return submitAuthForm("/api/auth/login", { email, password });
}

export async function registerWithPassword(payload: {
  workspaceName: string;
  name: string;
  email: string;
  password: string;
}): Promise<AuthFormResult> {
  return submitAuthForm("/api/auth/register", {
    workspace_name: payload.workspaceName,
    name: payload.name,
    email: payload.email,
    password: payload.password,
  });
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: { accept: "application/json" },
    cache: "no-store",
  });
}

async function submitAuthForm(path: string, body: Record<string, string>): Promise<AuthFormResult> {
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const payload = (await response.json()) as unknown;
    if (!response.ok) {
      return { ok: false, message: extractMessage(payload, response.statusText) };
    }
    if (!isAuthSession(payload)) {
      return { ok: false, message: "Authentication response was invalid" };
    }
    return { ok: true, session: payload };
  } catch {
    return { ok: false, message: "Unable to reach authentication service" };
  }
}

function isAuthSession(value: unknown): value is AuthSession {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.access_token === "string" &&
    typeof value.expires_at === "string" &&
    isRecord(value.identity)
  );
}

function extractMessage(payload: unknown, fallback: string): string {
  if (isRecord(payload)) {
    const error = payload.error;
    if (isRecord(error) && typeof error.message === "string") {
      return error.message;
    }
    if (typeof payload.message === "string") {
      return payload.message;
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  }
  return fallback || "Authentication failed";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
