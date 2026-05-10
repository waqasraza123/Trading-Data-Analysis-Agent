import { getServerApiProxyEnv } from "@/config/serverEnv";
import { isBackendAuthSession, setAuthSessionCookie } from "../session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  const env = getServerApiProxyEnv();
  const body = await request.text();
  try {
    const response = await fetch(`${env.apiBaseUrl}/auth/register`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": request.headers.get("content-type") || "application/json",
      },
      body,
      cache: "no-store",
    });
    const payload = await parseJson(response);
    if (response.ok && isBackendAuthSession(payload)) {
      await setAuthSessionCookie(payload.access_token);
    }
    return Response.json(payload, { status: response.status });
  } catch {
    return Response.json(
      { error: { code: "auth_backend_unavailable", message: "Unable to reach auth API" } },
      { status: 502 },
    );
  }
}

async function parseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { message: text };
  }
}
