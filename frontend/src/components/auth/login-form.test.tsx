import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/login-form";

const replace = vi.fn();
const refresh = vi.fn();
const { signInWithEmailAndPassword } = vi.hoisted(() => ({
  signInWithEmailAndPassword: vi.fn(),
}));

vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
}));
vi.mock("firebase/auth", () => ({
  signInWithEmailAndPassword,
  getMultiFactorResolver: vi.fn(),
  TotpMultiFactorGenerator: { FACTOR_ID: "totp" },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    replace.mockReset();
    refresh.mockReset();
    signInWithEmailAndPassword.mockReset();
  });

  it("shows accessible field errors before making a request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(await screen.findByText("Vui lòng nhập email.")).toBeDefined();
    expect(screen.getByText("Vui lòng nhập mật khẩu.")).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("signs in with Firebase email and exchanges its ID token", async () => {
    signInWithEmailAndPassword.mockResolvedValue({
      user: { getIdToken: vi.fn(async () => "firebase-email-token") },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
              email: "owner@tmigroup.vn",
              roles: ["APPLICANT"],
            },
          },
          meta: { request_id: "request-1" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<LoginForm next="/dashboard" />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(refresh).toHaveBeenCalledOnce();
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/firebase/exchange");
    expect(init?.credentials).toBe("include");
    expect(JSON.parse(String(init?.body))).toEqual({
      idToken: "firebase-email-token",
      accountType: "PUBLIC_USER",
      next: "/dashboard",
    });
    expect(signInWithEmailAndPassword).toHaveBeenCalledWith(
      { name: "firebase-auth" },
      "owner@tmigroup.vn",
      "correct horse battery staple",
    );
  });

  it("turns backend credential details into an actionable user message", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    signInWithEmailAndPassword.mockRejectedValue({
      code: "auth/invalid-credential",
    });
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "wrong password");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(
      await screen.findByText(
        "Email hoặc mật khẩu chưa đúng. Vui lòng kiểm tra lại.",
      ),
    ).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
