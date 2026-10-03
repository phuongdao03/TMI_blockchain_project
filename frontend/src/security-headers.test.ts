import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("frontend security headers", () => {
  it("allows protected provider media without allowing arbitrary media hosts", async () => {
    const routes = await nextConfig.headers!();
    const policy = routes[0]?.headers.find(
      (header) => header.key === "Content-Security-Policy",
    )?.value;
    expect(policy).toContain(
      "media-src 'self' https://api.cloudinary.com https://res.cloudinary.com",
    );
    expect(policy).not.toContain("media-src *");
  });

  it("excludes React Native storage from the browser bundle", () => {
    const config = { resolve: { alias: {} as Record<string, unknown> } };

    const result = nextConfig.webpack!(config, {} as never);

    expect(
      result.resolve.alias["@react-native-async-storage/async-storage"],
    ).toBe(false);
  });

  it("allows the Firebase Google popup bootstrap script", async () => {
    expect(nextConfig.headers).toBeDefined();

    const routes = await nextConfig.headers!();
    const contentSecurityPolicy = routes[0]?.headers.find(
      (header) => header.key === "Content-Security-Policy",
    )?.value;

    expect(contentSecurityPolicy).toContain(
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://apis.google.com",
    );
  });

  it("allows Firebase Auth relay frames without allowing arbitrary frames", async () => {
    expect(nextConfig.headers).toBeDefined();

    const routes = await nextConfig.headers!();
    const contentSecurityPolicy = routes[0]?.headers.find(
      (header) => header.key === "Content-Security-Policy",
    )?.value;

    expect(contentSecurityPolicy).toContain(
      "frame-src 'self' https://*.firebaseapp.com http://localhost:9099 http://127.0.0.1:9099",
    );
    expect(contentSecurityPolicy).not.toContain("frame-src *");
  });

  it("allows the proposal PDF to render in a same-origin frame only", async () => {
    const routes = await nextConfig.headers!();
    const documentHeaders = routes[0]?.headers;
    const proposalHeaders = routes.find(
      (route) => route.source === "/assets/institution/proposal-2026.pdf",
    )?.headers;

    expect(
      documentHeaders?.find(
        (header) => header.key === "Content-Security-Policy",
      )?.value,
    ).toContain("frame-ancestors 'none'");
    expect(
      proposalHeaders?.find(
        (header) => header.key === "Content-Security-Policy",
      )?.value,
    ).toContain("frame-ancestors 'self'");
    expect(
      proposalHeaders?.find((header) => header.key === "X-Frame-Options")
        ?.value,
    ).toBe("SAMEORIGIN");
  });
});
