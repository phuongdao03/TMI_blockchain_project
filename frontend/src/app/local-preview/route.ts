import { NextRequest, NextResponse } from "next/server";

// These destinations use the E2E mock API. This route is unavailable in builds
// and in ordinary development sessions without the explicit mock auth shim.
const screens = {
  "applicant-home": { persona: "applicant", path: "/dashboard" },
  "applicant-dossiers": { persona: "applicant", path: "/dossiers" },
  "applicant-dossier": {
    persona: "applicant",
    path: "/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac",
  },
  "applicant-new": { persona: "applicant", path: "/dossiers/new" },
  "applicant-certificates": { persona: "applicant", path: "/certificates" },
  "applicant-certificate": {
    persona: "applicant",
    path: "/certificates/7eaec2d2-c99a-42c9-8f1e-71462ba01ea0",
  },
  "reviewer-work": { persona: "reviewer", path: "/work-allocations" },
  "admin-home": { persona: "super-admin", path: "/admin/dashboard" },
  "admin-reviews": { persona: "super-admin", path: "/admin/reviews" },
  "admin-certificates": { persona: "super-admin", path: "/admin/certificates" },
  "admin-work": { persona: "super-admin", path: "/admin/work-allocations" },
} as const;

export function GET(request: NextRequest): NextResponse {
  const screen = request.nextUrl.searchParams.get("screen");
  const host = request.headers.get("host") ?? request.nextUrl.host;
  let previewOrigin: URL;
  try {
    previewOrigin = new URL(`http://${host}`);
  } catch {
    return new NextResponse(null, { status: 404 });
  }
  if (
    process.env.NODE_ENV !== "development" ||
    process.env.AUTH_E2E_SHIM !== "true" ||
    !["127.0.0.1", "localhost"].includes(previewOrigin.hostname) ||
    !screen ||
    !(screen in screens)
  ) {
    return new NextResponse(null, { status: 404 });
  }

  const { persona, path } = screens[screen as keyof typeof screens];
  const response = NextResponse.redirect(new URL(path, previewOrigin));
  response.headers.set("Cache-Control", "no-store");
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  const token =
    persona === "super-admin" ? "e2e-super-admin-access" : "e2e-access";
  response.cookies.set("cns_access", token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
  });
  response.cookies.set("cns_refresh", "e2e-refresh", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
  });
  response.cookies.set("cns_csrf", "e2e-csrf", {
    sameSite: "lax",
    path: "/",
  });
  response.cookies.set("cns_e2e_persona", persona, {
    sameSite: "lax",
    path: "/",
  });
  return response;
}
