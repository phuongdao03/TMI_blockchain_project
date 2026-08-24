import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  refresh: vi.fn(),
  resolveSignIn: vi.fn(),
  setQueryData: vi.fn(),
  signInWithPopup: vi.fn(),
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
  signInWithPopup: mocks.signInWithPopup,
  getMultiFactorResolver: () => ({
    hints: [{ factorId: "totp", uid: "factor-1" }],
    resolveSignIn: mocks.resolveSignIn,
  }),
  TotpMultiFactorGenerator: {
    FACTOR_ID: "totp",
    assertionForSignIn: (uid: string, code: string) => ({ uid, code }),
  },
}));

describe("GoogleOAuthButton MFA", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.values(mocks).forEach((mock) => mock.mockReset());
  });

  it("finishes a staff sign-in only after a valid TOTP challenge", async () => {
    mocks.signInWithPopup.mockRejectedValue({
      code: "auth/multi-factor-auth-required",
    });
    mocks.resolveSignIn.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "firebase-mfa-token") },
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

    const code = await screen.findByLabelText("Mã 6 số từ ứng dụng xác thực");
    await userEvent.type(code, "123456");
    await userEvent.click(screen.getByRole("button", { name: "Xác nhận mã" }));

    await waitFor(() => expect(mocks.resolveSignIn).toHaveBeenCalledOnce());
    expect(mocks.setQueryData).toHaveBeenCalledWith(
      ["auth", "me"],
      expect.objectContaining({ email: "staff@tmi.vn" }),
    );
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
    expect(screen.queryByText("auth/popup-blocked")).toBeNull();
  });
});
