import { getServerApiProxyEnv } from "@/config/serverEnv";
import { clearAuthSessionCookie, getAuthSessionToken } from "../session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(): Promise<Response> {
  const env = getServerApiProxyEnv();
  const token = await getAuthSessionToken();
  if (token) {
    try {
      await fetch(`${env.apiBaseUrl}/auth/logout`, {
        method: "POST",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${token}`,
          "content-type": "application/json",
        },
        body: JSON.stringify({ token }),
        cache: "no-store",
      });
    } catch {
      await clearAuthSessionCookie();
      return Response.json({ ok: true });
    }
  }
  await clearAuthSessionCookie();
  return Response.json({ ok: true });
}
