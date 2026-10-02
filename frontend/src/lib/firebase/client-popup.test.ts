import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  authStateReady: vi.fn(),
  initializePopup: vi.fn(),
}));

vi.mock("firebase/app", () => ({
  getApp: () => ({ name: "test-app" }),
  getApps: () => [{ name: "test-app" }],
  initializeApp: vi.fn(),
}));

vi.mock("firebase/auth", () => ({
  connectAuthEmulator: vi.fn(),
  getAuth: () => ({
    authStateReady: mocks.authStateReady,
    _popupRedirectResolver: { _initialize: mocks.initializePopup },
  }),
}));

describe("prepareGooglePopup", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
    mocks.authStateReady.mockReset();
    mocks.initializePopup.mockReset();
  });

  it("prepares Firebase auth and its popup iframe before enabling sign-in", async () => {
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_API_KEY", "test-api-key");
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN", "test.firebaseapp.com");
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_PROJECT_ID", "test-project");
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_APP_ID", "test-app-id");
    mocks.authStateReady.mockResolvedValue(undefined);
    mocks.initializePopup.mockResolvedValue(undefined);
    const { prepareGooglePopup } = await import("@/lib/firebase/client");

    await prepareGooglePopup();

    expect(mocks.authStateReady).toHaveBeenCalledOnce();
    expect(mocks.initializePopup).toHaveBeenCalledOnce();
    expect(mocks.authStateReady.mock.invocationCallOrder[0]!).toBeLessThan(
      mocks.initializePopup.mock.invocationCallOrder[0]!,
    );
  });
});
