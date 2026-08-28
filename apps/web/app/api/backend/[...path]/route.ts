import { getServerApiProxyEnv } from "@/config/serverEnv";
import { cookies } from "next/headers";
import { isTrustedMutationRequest, untrustedOriginResponse } from "../../auth/origin";

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

const forwardedRequestHeaders = ["authorization", "x-user-id", "x-workspace-id"];
const forwardedResponseHeaders = ["content-type"];

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function POST(request: Request, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function PATCH(request: Request, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

export async function DELETE(request: Request, context: RouteContext): Promise<Response> {
  return proxyRequest(request, context);
}

async function proxyRequest(request: Request, context: RouteContext): Promise<Response> {
  if (request.method !== "GET" && !isTrustedMutationRequest(request)) {
    return untrustedOriginResponse();
  }
  const params = await context.params;
  const path = params.path || [];
  if (path.length === 0) {
    return jsonError(400, "missing_proxy_path", "Backend proxy path is required");
  }

  const targetUrl = buildTargetUrl(request, path);
  const body = await request.arrayBuffer();

  try {
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: await buildForwardHeaders(request.headers),
      body: body.byteLength > 0 ? body : undefined,
      cache: "no-store",
    });
    return new Response(await response.arrayBuffer(), {
      status: response.status,
      statusText: response.statusText,
      headers: filterResponseHeaders(response.headers),
    });
  } catch {
    return jsonError(502, "backend_proxy_unavailable", "Unable to reach backend API");
  }
}

function buildTargetUrl(request: Request, path: string[]): string {
  const env = getServerApiProxyEnv();
  const requestUrl = new URL(request.url);
  const targetUrl = new URL(`${env.apiBaseUrl}/${path.map(encodeURIComponent).join("/")}`);
  requestUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.append(key, value);
  });
  return targetUrl.toString();
}

async function buildForwardHeaders(incomingHeaders: Headers): Promise<Headers> {
  const env = getServerApiProxyEnv();
  const headers = new Headers();
  headers.set("accept", incomingHeaders.get("accept") || "application/json");

  const contentType = incomingHeaders.get("content-type");
  if (contentType) {
    headers.set("content-type", contentType);
  }

  forwardedRequestHeaders.forEach((headerName) => {
    const value = incomingHeaders.get(headerName);
    if (value) {
      headers.set(headerName, value);
    }
  });

  if (env.adminApiKey) {
    headers.set(env.apiKeyHeaderName, env.adminApiKey);
  }

  if (!headers.has("authorization")) {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get(env.authSessionCookieName)?.value;
    if (sessionToken) {
      headers.set("authorization", `Bearer ${sessionToken}`);
    }
  }

  return headers;
}

function filterResponseHeaders(upstreamHeaders: Headers): Headers {
  const headers = new Headers();
  forwardedResponseHeaders.forEach((headerName) => {
    const value = upstreamHeaders.get(headerName);
    if (value) {
      headers.set(headerName, value);
    }
  });
  return headers;
}

function jsonError(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message } }, { status });
}
