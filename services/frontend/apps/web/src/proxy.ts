import { type NextRequest, NextResponse } from "next/server";

// The web app and the API share one origin: /api/* is passed to the backend (APPLY_API_URL, read on every
// request, so one built image works anywhere), keeping the session cookie first-party with SameSite=Lax and no
// CORS.
//
// Pages need a session: without the cookie, go to sign-in first (the API still checks the session itself;
// this only saves a flash of an empty screen).
const SESSION_COOKIES = ["apply_session", "__Host-apply_session"];
const PUBLIC = ["/sign-in", "/register", "/forgot-password", "/reset-password"];

function apiOrigin(): string {
  return (process.env.APPLY_API_URL ?? "http://127.0.0.1:8110").replace(/\/$/, "");
}

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (pathname.startsWith("/api/")) {
    return NextResponse.rewrite(new URL(`${pathname}${search}`, apiOrigin()));
  }
  if (PUBLIC.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return NextResponse.next();
  if (SESSION_COOKIES.some((name) => request.cookies.has(name))) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = "/sign-in";
  url.search = pathname === "/" ? "" : `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/|favicon.ico|.*\\.(?:svg|png|jpg|ico|woff2?)$).*)"],
};
