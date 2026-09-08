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
  GoogleAuthProvider: vi.fn(),
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

  it("uses a full-page redirect for Google sign-in on mobile browsers", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    );
    mocks.signInWithRedirect.mockResolvedValue(undefined);

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    await waitFor(() =>
      expect(mocks.signInWithRedirect).toHaveBeenCalledOnce(),
    );
    expect(mocks.signInWithPopup).not.toHaveBeenCalled();
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

  it("clears the pending marker when a mobile redirect cannot start", async () => {
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148 Safari/604.1",
    );
    mocks.signInWithRedirect.mockRejectedValue({
      code: "auth/unauthorized-domain",
    });

    render(<GoogleOAuthButton accountType="PUBLIC_USER" />);
    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Tên miền hiện tại chưa được cho phép đăng nhập Google.",
    );
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

  it("explains how to recover from a blocked popup without exposing a code", async () => {
    mocks.signInWithPopup.mockRejectedValue({ code: "auth/popup-blocked" });
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
