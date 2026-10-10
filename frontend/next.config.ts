import type { NextConfig } from "next";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const securityHeaders = [
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "base-uri 'self'",
      "frame-ancestors 'none'",
      "form-action 'self'",
      "object-src 'none'",
      `script-src 'self' 'unsafe-inline'${
        process.env.NODE_ENV === "production" ? "" : " 'unsafe-eval'"
      } https://apis.google.com`,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https:",
      "media-src 'self' https://api.cloudinary.com https://res.cloudinary.com",
      `connect-src 'self' https:${
        process.env.NODE_ENV === "production"
          ? ""
          : " ws: http://localhost:9099 http://127.0.0.1:9099"
      }`,
      `frame-src 'self' https://*.firebaseapp.com${
        process.env.NODE_ENV === "production"
          ? ""
          : " http://localhost:9099 http://127.0.0.1:9099"
      }`,
      "font-src 'self' data:",
    ].join("; "),
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), geolocation=(self), microphone=()",
  },
  ...(process.env.NODE_ENV === "production"
    ? [
        {
          key: "Strict-Transport-Security",
          value: "max-age=31536000; includeSubDomains",
        },
      ]
    : []),
];

const sameOriginPdfHeaders = securityHeaders.map((header) => {
  if (header.key === "Content-Security-Policy") {
    return {
      ...header,
      value: header.value.replace(
        "frame-ancestors 'none'",
        "frame-ancestors 'self'",
      ),
    };
  }
  if (header.key === "X-Frame-Options") {
    return { ...header, value: "SAMEORIGIN" };
  }
  return header;
});

const qrRedirectHeaders = [
  { key: "Cache-Control", value: "no-store" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Robots-Tag", value: "noindex, nofollow" },
];

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  output: "standalone",
  images: {
    localPatterns: [
      {
        pathname: "/assets/brand/**",
        search: "",
      },
      {
        pathname: "/assets/institution/**",
        search: "",
      },
    ],
  },
  turbopack: {
    root: dirname(fileURLToPath(import.meta.url)),
  },
  webpack(config) {
    // MetaMask SDK supports React Native too, but this application only ships
    // a browser bundle. Exclude its optional native storage adapter.
    config.resolve.alias["@react-native-async-storage/async-storage"] = false;

    if (
      process.env.NODE_ENV !== "production" &&
      process.env.AUTH_E2E_SHIM === "true"
    ) {
      config.resolve.alias["firebase/auth"] = resolve(
        dirname(fileURLToPath(import.meta.url)),
        "e2e/firebase-auth-shim.ts",
      );
    }
    return config;
  },
  async redirects() {
    return [
      {
        source: "/tai-san/:slug",
        destination: "/works/:slug",
        permanent: true,
      },
      {
        source: "/kiem-tra/:token",
        destination: "/verify/:token",
        permanent: true,
      },
    ];
  },
  async headers() {
    return [
      { source: "/((?!__/auth/).*)", headers: securityHeaders },
      {
        source: "/sw.js",
        headers: [
          {
            key: "Cache-Control",
            value: "no-cache, no-store, must-revalidate",
          },
        ],
      },
      {
        source: "/assets/institution/proposal-2026.pdf",
        headers: sameOriginPdfHeaders,
      },
      {
        source: "/api/v1/certificates/:id/pdf",
        headers: sameOriginPdfHeaders,
      },
      { source: "/r/:token", headers: qrRedirectHeaders },
      { source: "/verify/:token", headers: qrRedirectHeaders },
    ];
  },
  async rewrites() {
    const apiBaseUrl = (
      process.env.API_BASE_URL ??
      process.env.BACKEND_URL ??
      "http://localhost:8000"
    ).replace(/\/$/, "");
    const firebaseAuthDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN;
    const firebaseAuthRewrite =
      firebaseAuthDomain &&
      /^[a-z0-9-]+\.firebaseapp\.com$/i.test(firebaseAuthDomain)
        ? [
            {
              source: "/__/auth/:path*",
              destination: `https://${firebaseAuthDomain}/__/auth/:path*`,
            },
          ]
        : [];
    return [
      ...firebaseAuthRewrite,
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`,
      },
      {
        source: "/r/:token",
        destination: `${apiBaseUrl}/r/:token`,
      },
    ];
  },
};

export default nextConfig;
