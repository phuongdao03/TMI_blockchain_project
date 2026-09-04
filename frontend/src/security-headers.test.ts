import { describe, expect, it } from "vitest";

import nextConfig from "../next.config";

describe("frontend security headers", () => {
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
});
