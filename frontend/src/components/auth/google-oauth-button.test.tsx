import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  setQueryData: vi.fn(),
  getRedirectResult: vi.fn(),
  setCustomParameters: vi.fn(),
  signInWithPopup: vi.fn(),
  signInWithRedirect: vi.fn(),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ setQueryData: mocks.setQueryData }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mocks.replace, refresh: mocks.refresh }),
}));
vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
}));
vi.mock("firebase/auth", () => ({
  GoogleAuthProvider: class {
    setCustomParameters = mocks.setCustomParameters;
  },
  getRedirectResult: mocks.getRedirectResult,
  signInWithPopup: mocks.signInWithPopup,
  signInWithRedirect: mocks.signInWithRedirect,
}));

describe("GoogleOAuthButton", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.values(mocks).forEach((mock) => mock.mockReset());
    sessionStorage.clear();
    mocks.getRedirectResult.mockResolvedValue(null);
  });

  it("uses a popup on the first mobile tap so Safari does not depend on cross-site redirect storage", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    );
    mocks.signInWithPopup.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "mobile-popup-token") },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "user-mobile",
              email: "mobile@tmi.vn",
              roles: ["PUBLIC_USER"],
            },
          },
          meta: { request_id: "request-mobile" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    await waitFor(() => expect(mocks.signInWithPopup).toHaveBeenCalledOnce());
    expect(mocks.signInWithRedirect).not.toHaveBeenCalled();
    expect(
      sessionStorage.getItem("tmi.google-oauth.redirect-pending"),
    ).toBeNull();
    expect(mocks.setCustomParameters).toHaveBeenCalledWith({
      prompt: "select_account",
    });
  });

  it("falls back to redirect when the browser blocks the popup", async () => {
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });
    mocks.signInWithRedirect.mockResolvedValue(undefined);

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    await waitFor(() =>
      expect(mocks.signInWithRedirect).toHaveBeenCalledOnce(),
    );
    expect(sessionStorage.getItem("tmi.google-oauth.redirect-pending")).toBe(
      "1",
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("does not use redirect fallback on mobile browsers", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    );
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "cho phép cửa sổ bật lên",
    );
    expect(mocks.signInWithRedirect).not.toHaveBeenCalled();
    expect(
      sessionStorage.getItem("tmi.google-oauth.redirect-pending"),
    ).toBeNull();
  });

  it("finishes authentication after returning from the mobile redirect", async () => {
    sessionStorage.setItem("tmi.google-oauth.redirect-pending", "1");
    mocks.getRedirectResult.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "redirect-token") },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "user-mobile",
              email: "mobile@tmi.vn",
              roles: ["PUBLIC_USER"],
            },
          },
          meta: { request_id: "request-mobile" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "mobile@tmi.vn" }),
      ),
    );
    expect(
      sessionStorage.getItem("tmi.google-oauth.redirect-pending"),
    ).toBeNull();
    expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
  });

  it("checks Firebase redirect completion even when Safari lost the local marker", async () => {
    mocks.getRedirectResult.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "recovered-token") },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "user-recovered",
              email: "recovered@tmi.vn",
              roles: ["PUBLIC_USER"],
            },
          },
          meta: { request_id: "request-recovered" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "recovered@tmi.vn" }),
      ),
    );
  });

  it("finishes a consumed redirect credential after the effect is cleaned up", async () => {
    sessionStorage.setItem("tmi.google-oauth.redirect-pending", "1");
    let resolveRedirect!: (credential: {
      user: { getIdToken: () => Promise<string> };
    }) => void;
    mocks.getRedirectResult.mockReturnValue(
      new Promise((resolve) => {
        resolveRedirect = resolve;
      }),
    );
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "user-mobile-remount",
              email: "mobile-remount@tmi.vn",
              roles: ["PUBLIC_USER"],
            },
          },
          meta: { request_id: "request-mobile-remount" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const view = render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    view.unmount();
    resolveRedirect({
      user: { getIdToken: vi.fn(async () => "redirect-remount-token") },
    });

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "mobile-remount@tmi.vn" }),
      ),
    );
    expect(mocks.replace).toHaveBeenCalledWith("/dashboard");
  });

  it("explains how to recover when a mobile popup cannot start", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148 Safari/604.1",
    );
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "cho phép cửa sổ bật lên",
    );
    expect(mocks.signInWithRedirect).not.toHaveBeenCalled();
    expect(
      sessionStorage.getItem("tmi.google-oauth.redirect-pending"),
    ).toBeNull();
  });

  it("finishes staff sign-in after Firebase authentication", async () => {
    mocks.signInWithPopup.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "firebase-token") },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: { id: "user-1", email: "staff@tmi.vn", roles: ["MODERATOR"] },
          },
          meta: { request_id: "request-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    await waitFor(() =>
      expect(mocks.setQueryData).toHaveBeenCalledWith(
        ["auth", "me"],
        expect.objectContaining({ email: "staff@tmi.vn" }),
      ),
    );
    expect(screen.queryByText(/mã 6 số/i)).toBeNull();
    expect(mocks.replace).toHaveBeenCalledWith("/reviews");
  });

  it("explains a blocked popup when the redirect fallback also fails", async () => {
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });
    mocks.signInWithRedirect.mockRejectedValue({ code: "auth/popup-blocked" });
    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );
    expect(
      await screen.findByText(
        "Trình duyệt đã chặn cửa sổ đăng nhập. Hãy cho phép popup rồi thử lại.",
      ),
    ).toBeDefined();
  });
});
