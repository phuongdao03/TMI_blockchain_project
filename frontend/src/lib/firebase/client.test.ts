import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveFirebaseAuthDomain } from "@/lib/firebase/client";

describe("resolveFirebaseAuthDomain", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("uses the app origin for Android Firebase Auth when the proxy is enabled", () => {
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH", "true");
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    expect(resolveFirebaseAuthDomain("tmi-blockchain.firebaseapp.com")).toBe(
      "decu.tinhhoaviet.org.vn",
    );
  });

  it("uses the proxied handler on the public production domain", () => {
    vi.stubEnv("NEXT_PUBLIC_APP_BASE_URL", "https://decu.tinhhoaviet.org.vn");
    expect(resolveFirebaseAuthDomain("tmi-blockchain.firebaseapp.com")).toBe(
      "decu.tinhhoaviet.org.vn",
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
