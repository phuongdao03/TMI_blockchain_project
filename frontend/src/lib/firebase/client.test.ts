import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveFirebaseAuthDomain } from "@/lib/firebase/client";

describe("resolveFirebaseAuthDomain", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  function emulateMobile() {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    );
  }

  it("uses the app origin for mobile Firebase Auth when the proxy is enabled", () => {
    emulateMobile();
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH", "true");
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    expect(resolveFirebaseAuthDomain("tmi-blockchain.firebaseapp.com")).toBe(
      "decu.tinhhoaviet.org.vn",
    );
  });

  it("uses the proxied handler on the public production domain", () => {
    emulateMobile();
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    expect(resolveFirebaseAuthDomain("tmi-blockchain.firebaseapp.com")).toBe(
      "decu.tinhhoaviet.org.vn",
    );
  });

  it("keeps the working Firebase popup handler on desktop", () => {
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH", "true");
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    expect(resolveFirebaseAuthDomain("tmi-blockchain.firebaseapp.com")).toBe(
      "tmi-blockchain.firebaseapp.com",
    );
  });

  it("keeps the configured handler on other production domains", () => {
    expect(resolveFirebaseAuthDomain("project.firebaseapp.com")).toBe(
      "project.firebaseapp.com",
    );
  });

  it("keeps the configured Firebase domain outside production", () => {
    expect(resolveFirebaseAuthDomain("project.firebaseapp.com")).toBe(
      "project.firebaseapp.com",
    );
  });
});
