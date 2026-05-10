import { NextResponse, type NextRequest } from "next/server";
import { defaultAuthSessionCookieName } from "@/config/serverEnv";

const publicPaths = new Set(["/login", "/register", "/icon.svg"]);

export function middleware(request: NextRequest) {
  if (process.env.NEXT_PUBLIC_AUTH_MODE !== "session") {
    return NextResponse.next();
  }
  const pathname = request.nextUrl.pathname;
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }
  const cookieName = process.env.WEB_AUTH_SESSION_COOKIE || defaultAuthSessionCookieName;
  if (request.cookies.get(cookieName)?.value) {
    return NextResponse.next();
  }
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", pathname);
  return NextResponse.redirect(loginUrl);
}

function isPublicPath(pathname: string): boolean {
  return (
    publicPaths.has(pathname) ||
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname.includes(".")
  );
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
