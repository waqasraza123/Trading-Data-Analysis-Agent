import { cookies } from "next/headers";
import { getServerApiProxyEnv } from "@/config/serverEnv";

const authCookieMaxAgeSeconds = 60 * 60 * 24;

export type BackendAuthSession = {
  access_token: string;
  token_type: string;
  expires_at: string;
  identity: unknown;
};

export async function setAuthSessionCookie(token: string, expiresAt: string): Promise<void> {
  const env = getServerApiProxyEnv();
  const cookieStore = await cookies();
  const maxAge = sessionCookieMaxAge(expiresAt);
  cookieStore.set(env.authSessionCookieName, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge,
  });
}

function sessionCookieMaxAge(expiresAt: string): number {
  const expiresAtMilliseconds = Date.parse(expiresAt);
  if (!Number.isFinite(expiresAtMilliseconds)) {
    return authCookieMaxAgeSeconds;
  }
  const seconds = Math.floor((expiresAtMilliseconds - Date.now()) / 1000);
  return Math.max(1, seconds);
}

export async function clearAuthSessionCookie(): Promise<void> {
  const env = getServerApiProxyEnv();
  const cookieStore = await cookies();
  cookieStore.set(env.authSessionCookieName, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
}

export async function getAuthSessionToken(): Promise<string | null> {
  const env = getServerApiProxyEnv();
  const cookieStore = await cookies();
  return cookieStore.get(env.authSessionCookieName)?.value || null;
}

export function isBackendAuthSession(value: unknown): value is BackendAuthSession {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return typeof record.access_token === "string" && typeof record.expires_at === "string";
}
