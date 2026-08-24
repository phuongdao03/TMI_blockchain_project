import { afterEach, describe, expect, it, vi } from "vitest";

import nextConfig from "../next.config";

describe("public route compatibility", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("permanently redirects former public addresses to canonical routes", async () => {
    const redirects = await nextConfig.redirects?.();

    expect(redirects).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/tai-san/:slug",
          destination: "/works/:slug",
          permanent: true,
        }),
        expect.objectContaining({
          source: "/kiem-tra/:token",
          destination: "/verify/:token",
          permanent: true,
        }),
      ]),
    );
  });

  it("proxies opaque QR redirects without exposing a backend-only route", async () => {
    vi.stubEnv("API_BASE_URL", "https://api.example.test");
    const rewrites = await nextConfig.rewrites?.();

    expect(rewrites).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/r/:token",
          destination: "https://api.example.test/r/:token",
        }),
      ]),
    );
  });

  it("prevents an opaque QR token from being cached or forwarded as a referrer", async () => {
    const headers = await nextConfig.headers?.();

    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/r/:token",
          headers: expect.arrayContaining([
            expect.objectContaining({
              key: "Cache-Control",
              value: "no-store",
            }),
            expect.objectContaining({
              key: "Referrer-Policy",
              value: "no-referrer",
            }),
            expect.objectContaining({
              key: "X-Robots-Tag",
              value: "noindex, nofollow",
            }),
          ]),
        }),
      ]),
    );
  });

  it("prevents certificate verification tokens from being indexed or cached", async () => {
    const headers = await nextConfig.headers?.();

    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: "/verify/:token",
          headers: expect.arrayContaining([
            expect.objectContaining({
              key: "Cache-Control",
              value: "no-store",
            }),
            expect.objectContaining({
              key: "Referrer-Policy",
              value: "no-referrer",
            }),
            expect.objectContaining({
              key: "X-Robots-Tag",
              value: "noindex, nofollow",
            }),
          ]),
        }),
      ]),
    );
  });
});
