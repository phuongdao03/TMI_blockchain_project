import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/login-form";

const replace = vi.fn();
const refresh = vi.fn();
const { sendEmailVerification, signInWithEmailAndPassword, signOut } =
  vi.hoisted(() => ({
    sendEmailVerification: vi.fn(),
    signInWithEmailAndPassword: vi.fn(),
    signOut: vi.fn(),
  }));

vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
}));
vi.mock("firebase/auth", () => ({
  sendEmailVerification,
  signInWithEmailAndPassword,
  signOut,
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
    sendEmailVerification.mockReset();
    signInWithEmailAndPassword.mockReset();
    signOut.mockReset();
  });

  it("shows accessible field errors before making a request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(await screen.findByText("Vui lòng nhập email.")).toBeDefined();
    expect(screen.getByText("Vui lòng nhập mật khẩu.")).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps account routing and staff provisioning details out of the form", () => {
    render(<LoginForm />, { wrapper: Wrapper });

    expect(
      screen.getByText(
        "Truy cập không gian hồ sơ để theo dõi tiến trình, phản hồi và chứng thư của bạn.",
      ),
    ).toBeDefined();
    expect(screen.queryByText(/một tài khoản cho mọi hành trình/i)).toBeNull();
    expect(screen.queryByText(/nhân sự chỉ được tạo qua lời mời/i)).toBeNull();
    expect(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    ).toBeDefined();
  });

  it("signs in with Firebase email and exchanges its ID token", async () => {
    signInWithEmailAndPassword.mockResolvedValue({
      user: {
        emailVerified: true,
        getIdToken: vi.fn(async () => "firebase-email-token"),
      },
    });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          data: {
            user: {
              id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
              email: "owner@tmigroup.vn",
              roles: ["USER"],
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

  it("sends a verification email instead of exchanging an unverified Firebase identity", async () => {
    const firebaseUser = {
      emailVerified: false,
      getIdToken: vi.fn(async () => "unverified-firebase-token"),
    };
    signInWithEmailAndPassword.mockResolvedValue({ user: firebaseUser });
    sendEmailVerification.mockResolvedValue(undefined);
    signOut.mockResolvedValue(undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "blockchainadmin@gmail.com",
    );
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "valid password");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Email chưa được xác minh",
    );
    expect(sendEmailVerification).toHaveBeenCalledWith(firebaseUser, {
      url: `${window.location.origin}/login`,
    });
    expect(signOut).toHaveBeenCalledWith({ name: "firebase-auth" });
    expect(fetchMock).not.toHaveBeenCalled();
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

  it("explains when Firebase email sign-in is disabled", async () => {
    signInWithEmailAndPassword.mockRejectedValue({
      code: "auth/operation-not-allowed",
    });
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "valid password");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Đăng nhập bằng email chưa được cấu hình",
    );
  });

  it("explains when a Firebase account is not linked to the platform account", async () => {
    signInWithEmailAndPassword.mockResolvedValue({
      user: {
        emailVerified: true,
        getIdToken: vi.fn(async () => "firebase-admin-token"),
      },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: {
            code: "OAUTH_ACCOUNT_LINK_REQUIRED",
            message: "Existing account must be linked explicitly.",
          },
          meta: { request_id: "request-admin-link" },
        }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "admin@example.vn",
    );
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "valid password");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(
      await screen.findByText(
        "Tài khoản chưa được liên kết hoàn tất. Vui lòng liên hệ quản trị hệ thống.",
      ),
    ).toBeDefined();
  });

  it("distinguishes a rejected Firebase identity from an inactive account", async () => {
    signInWithEmailAndPassword.mockResolvedValue({
      user: {
        emailVerified: true,
        getIdToken: vi.fn(async () => "firebase-invalid-token"),
      },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: {
            code: "OAUTH_IDENTITY_INVALID",
            message: "Firebase identity validation failed.",
          },
          meta: { request_id: "request-firebase-invalid" },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<LoginForm />, { wrapper: Wrapper });

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "admin@example.vn",
    );
    await userEvent.type(screen.getByLabelText("Mật khẩu"), "valid password");
    await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Không thể xác minh phiên đăng nhập Firebase",
    );
  });
});
