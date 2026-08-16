import { NextRequest, NextResponse } from "next/server";

import { isPreviewRelease, isPreviewRestrictedPath } from "@/lib/release-mode";

export function proxy(request: NextRequest) {
  if (isPreviewRelease() && isPreviewRestrictedPath(request.nextUrl.pathname)) {
    const destination = request.nextUrl.clone();
    destination.pathname = "/dashboard";
    destination.search = "?notice=preview";
    return NextResponse.redirect(destination);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/activity/:path*",
    "/certificates/:path*",
    "/council/:path*",
    "/dossiers/:path*",
    "/notifications/:path*",
    "/payments/:path*",
    "/reviews/:path*",
    "/vote-history/:path*",
  ],
};
