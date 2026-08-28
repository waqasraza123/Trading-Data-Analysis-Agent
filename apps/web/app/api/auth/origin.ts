export function isTrustedMutationRequest(request: Request): boolean {
  if (request.headers.get("sec-fetch-site") === "cross-site") {
    return false;
  }
  const origin = request.headers.get("origin");
  if (!origin) {
    return true;
  }
  try {
    return new URL(origin).origin === new URL(request.url).origin;
  } catch {
    return false;
  }
}

export function untrustedOriginResponse(): Response {
  return Response.json(
    { error: { code: "untrusted_origin", message: "Request origin is not allowed" } },
    { status: 403 },
  );
}
