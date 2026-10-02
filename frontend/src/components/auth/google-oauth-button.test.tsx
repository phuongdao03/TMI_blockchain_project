import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  setQueryData: vi.fn(),
  getRedirectResult: vi.fn(),
  signInWithPopup: vi.fn(),
  signInWithRedirect: vi.fn(),
  prepareGooglePopup: vi.fn(),
}));

vi.mock("@tanstack/react-query", () => {
  const queryClient = { setQueryData: mocks.setQueryData };
  return { useQueryClient: () => queryClient };
});
vi.mock("next/navigation", () => {
  const router = { replace: mocks.replace, refresh: mocks.refresh };
  return { useRouter: () => router };
});
vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
  prepareGooglePopup: mocks.prepareGooglePopup,
}));
vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: class {
    setCustomParameters = vi.fn();
  },
  getRedirectResult: mocks.getRedirectResult,
  signInWithPopup: mocks.signInWithPopup,
  signInWithRedirect: mocks.signInWithRedirect,
}));

function mockExchange(email: string, roles = ["PUBLIC_USER"]) {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        success: true,
        data: { user: { id: "user-1", email, roles } },
        meta: { request_id: "request-1" },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ),
  );
}

describe("GoogleOAuthButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
    Object.values(mocks).forEach((mock) => mock.mockReset());
    sessionStorage.clear();
    mocks.getRedirectResult.mockResolvedValue(null);
    mocks.prepareGooglePopup.mockResolvedValue(undefined);
  });

  it("uses same-origin redirect on Android and completes after returning", async () => {
    vi.stubEnv("NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH", "true");
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/125 Mobile Safari/537.36",
    );
    mocks.signInWithRedirect.mockResolvedValue(undefined);
    const { unmount } = render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(screen.getByRole("button", { name: /Google/ }));
    expect(mocks.signInWithRedirect).toHaveBeenCalledOnce();
    expect(mocks.signInWithPopup).not.toHaveBeenCalled();
    expect(sessionStorage.getItem("cns.google-oauth.redirect-pending")).toBe(
      "1",
    );
    unmount();

    mocks.getRedirectResult.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "android-token") },
    });
    mockExchange("android@cns.vn");
    // A redirect reloads the page, so mount a fresh button for the return trip.
    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await waitFor(() =>
      expect(mocks.replace).toHaveBeenCalledWith("/dashboard"),
    );
    expect(
      sessionStorage.getItem("cns.google-oauth.redirect-pending"),
    ).toBeNull();
  });

  it("waits for the Google popup helper before the first mobile tap", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    );
    let finishPreparation!: () => void;
    mocks.prepareGooglePopup.mockReturnValue(
      new Promise<void>((resolve) => {
        finishPreparation = resolve;
      }),
    );
    mocks.signInWithPopup.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "first-tap-token") },
    });
    mockExchange("first-tap@cns.vn");

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    const button = screen.getByRole("button", { name: /Google/ });
    expect(button.hasAttribute("disabled")).toBe(true);
    expect(mocks.signInWithPopup).not.toHaveBeenCalled();

    finishPreparation();
    await waitFor(() => expect(button.hasAttribute("disabled")).toBe(false));
    await userEvent.click(button);

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "first-tap@cns.vn" }),
      ),
    );
    expect(mocks.signInWithPopup).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it.each([
    [
      "Android",
      "Mozilla/5.0 (Linux; Android 15; Pixel 8) AppleWebKit/537.36 Chrome/125 Mobile Safari/537.36",
    ],
    [
      "iPhone",
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    ],
  ])(
    "finishes Google login or registration on %s without a redirect",
    async (_, agent) => {
      if (_ === "iPhone")
        vi.stubEnv("NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH", "true");
      vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(agent);
      mocks.signInWithPopup.mockResolvedValue({
        user: { getIdToken: vi.fn(async () => "mobile-token") },
      });
      mockExchange("mobile@cns.vn");

      render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
      await userEvent.click(
        await screen.findByRole("button", { name: "Tiếp tục với Google" }),
      );

      await waitFor(() =>
        expect(mocks.setQueryData).toHaveBeenCalledWith(
          ["auth", "me"],
          expect.objectContaining({ email: "mobile@cns.vn" }),
        ),
      );
      expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
      expect(mocks.signInWithRedirect).not.toHaveBeenCalled();
      expect(screen.queryByRole("alert")).toBeNull();
    },
  );

  it("ignores a stale mobile redirect marker", async () => {
    sessionStorage.setItem("cns.google-oauth.redirect-pending", "1");
    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);

    await waitFor(() => expect(mocks.getRedirectResult).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(
      sessionStorage.getItem("cns.google-oauth.redirect-pending"),
    ).toBeNull();
  });

  it("finishes an earlier redirect if the user returns during deployment", async () => {
    sessionStorage.setItem("cns.google-oauth.redirect-pending", "1");
    mocks.getRedirectResult.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "old-redirect-token") },
    });
    mockExchange("returning@cns.vn");

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "returning@cns.vn" }),
      ),
    );
    expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
    expect(
      sessionStorage.getItem("cns.google-oauth.redirect-pending"),
    ).toBeNull();
  });

  it("explains when a mobile browser blocks the Google window", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/125 Mobile Safari/537.36",
    );
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });
    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Trình duyệt đã chặn cửa sổ đăng nhập Google",
    );
    expect(mocks.signInWithRedirect).not.toHaveBeenCalled();
  });

  it("keeps staff routing after Google authentication", async () => {
    mocks.signInWithPopup.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "firebase-token") },
    });
    mockExchange("staff@cns.vn", ["MODERATOR"]);

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Tiếp tục với Google" }),
    );

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "staff@cns.vn" }),
      ),
    );
    expect(mocks.replace).toHaveBeenCalledWith("/work-allocations");
  });
});
