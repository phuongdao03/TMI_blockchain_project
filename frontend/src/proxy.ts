import { NextRequest, NextResponse } from "next/server";

import { isPreviewRelease, isPreviewRestrictedPath } from "@/lib/release-mode";

export function proxy(request: NextRequest) {
  if (isPreviewRelease() && isPreviewRestrictedPath(request.nextUrl.pathname)) {
    const destination = request.nextUrl.clone();
    destination.pathname = "/workspace";
    destination.search = "?notice=preview";
    return NextResponse.redirect(destination);
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.delete("x-thv-request-destination");
  const requestedDestination = `${request.nextUrl.pathname}${request.nextUrl.search}`;
  requestHeaders.set(
    "x-thv-request-destination",
    requestedDestination.length <= 1024 ? requestedDestination : "/workspace",
  );
  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/account/:path*",
    "/activity/:path*",
    "/attendance/:path*",
    "/blockchain/:path*",
    "/certificates/:path*",
    "/dashboard/:path*",
    "/dossiers/:path*",
    "/help/:path*",
    "/leave/:path*",
    "/notifications/:path*",
    "/overtime/:path*",
    "/payments/:path*",
    "/reviews/:path*",
    "/work-allocations/:path*",
    "/workspace/:path*",
  ],
};
