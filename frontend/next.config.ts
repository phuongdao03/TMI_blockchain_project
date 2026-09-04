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
    value: "camera=(), geolocation=(), microphone=()",
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

const qrRedirectHeaders = [
  { key: "Cache-Control", value: "no-store" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Robots-Tag", value: "noindex, nofollow" },
];

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  output: "standalone",
  images: {
    localPatterns: [
      {
        pathname: "/assets/brand/**",
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
      { source: "/:path*", headers: securityHeaders },
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
    return [
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
