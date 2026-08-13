import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegisterForm } from "@/components/auth/register-form";

const replace = vi.fn();
const refresh = vi.fn();
const setQueryData = vi.fn();
const firebaseMocks = vi.hoisted(() => ({
  createUserWithEmailAndPassword: vi.fn(),
  sendEmailVerification: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
}));

vi.mock("@tanstack/react-query", () => ({
  useQueryClient: () => ({ setQueryData }),
}));

vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({}),
}));

vi.mock("firebase/auth", () => ({
  createUserWithEmailAndPassword: firebaseMocks.createUserWithEmailAndPassword,
  GoogleAuthProvider: vi.fn(),
  sendEmailVerification: firebaseMocks.sendEmailVerification,
  signOut: firebaseMocks.signOut,
  signInWithPopup: vi.fn(async () => ({
    user: { getIdToken: vi.fn(async () => "firebase-test-token") },
  })),
}));

describe("RegisterForm", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    replace.mockReset();
    refresh.mockReset();
    setQueryData.mockReset();
    firebaseMocks.createUserWithEmailAndPassword.mockReset();
    firebaseMocks.sendEmailVerification.mockReset();
    firebaseMocks.signOut.mockReset();
    firebaseMocks.signOut.mockResolvedValue(undefined);
  });

  it("rejects mismatched passwords without a network request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "different horse battery value",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(
      await screen.findByText("Mật khẩu xác nhận không khớp."),
    ).toBeDefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("creates the email identity in Firebase and sends a verification link", async () => {
    const user = { uid: "firebase-user-1" };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    firebaseMocks.createUserWithEmailAndPassword.mockResolvedValue({ user });
    firebaseMocks.sendEmailVerification.mockResolvedValue(undefined);
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(await screen.findByRole("status")).toBeDefined();
    expect(screen.getByText(/hướng dẫn xác minh đã được gửi/i)).toBeDefined();
    expect(firebaseMocks.createUserWithEmailAndPassword).toHaveBeenCalledWith(
      {},
      "owner@tmigroup.vn",
      "correct horse battery staple",
    );
    expect(firebaseMocks.sendEmailVerification).toHaveBeenCalledWith(
      user,
      expect.objectContaining({
        url: expect.stringContaining("accountType=PUBLIC_USER"),
      }),
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits the selected organization applicant account type", async () => {
    const user = { uid: "firebase-organization-1" };
    firebaseMocks.createUserWithEmailAndPassword.mockResolvedValue({ user });
    firebaseMocks.sendEmailVerification.mockResolvedValue(undefined);
    render(<RegisterForm />);

    await userEvent.click(screen.getByRole("radio", { name: /Tổ chức/i }));
    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "organization@tmigroup.vn",
    );
    await userEvent.type(
      screen.getByLabelText("Mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu"),
      "correct horse battery staple",
    );
    await userEvent.click(screen.getByRole("button", { name: "Đăng ký" }));

    expect(firebaseMocks.sendEmailVerification).toHaveBeenCalledWith(
      user,
      expect.objectContaining({
        url: expect.stringContaining("accountType=ORGANIZATION_APPLICANT"),
      }),
    );
  });

  it("offers a browse-only account intent without dossier privileges", () => {
    render(<RegisterForm />);

    expect(
      screen.getByRole("radio", { name: /Khám phá công khai/i }),
    ).toBeDefined();
  });

  it("starts Google OAuth with the selected account intent and shows provider errors", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          success: false,
          error: {
            code: "OAUTH_PROVIDER_UNAVAILABLE",
            message: "provider unavailable",
            details: {},
            request_id: "request-google-1",
          },
        }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(<RegisterForm />);

    await userEvent.click(
      screen.getByRole("button", { name: "Tiếp tục với Google" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Đăng nhập Google đang tạm thời gián đoạn",
    );
    const [, options] = fetchMock.mock.calls[0] ?? [];
    expect(JSON.parse(String(options?.body))).toMatchObject({
      accountType: "PUBLIC_USER",
      idToken: "firebase-test-token",
    });
  });
});
