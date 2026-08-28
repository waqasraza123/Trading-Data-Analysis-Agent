import { getServerApiProxyEnv } from "@/config/serverEnv";
import { isTrustedMutationRequest, untrustedOriginResponse } from "../origin";
import { isBackendAuthSession, setAuthSessionCookie } from "../session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: Request): Promise<Response> {
  if (!isTrustedMutationRequest(request)) {
    return untrustedOriginResponse();
  }
  return authenticate(request, "/auth/login");
}

async function authenticate(request: Request, path: string): Promise<Response> {
  const env = getServerApiProxyEnv();
  const body = await request.text();
  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
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
      await setAuthSessionCookie(payload.access_token, payload.expires_at);
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
