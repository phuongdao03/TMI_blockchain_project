import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RegisterForm } from "@/components/auth/register-form";
import { authApi } from "@/lib/api/client";

const replace = vi.fn();
const refresh = vi.fn();
const setQueryData = vi.fn();
const firebaseMocks = vi.hoisted(() => ({
  createUserWithEmailAndPassword: vi.fn(),
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
  prepareGooglePopup: async () => undefined,
  usesSameOriginFirebaseAuth: () => false,
}));

vi.mock("firebase/auth", () => ({
  createUserWithEmailAndPassword: firebaseMocks.createUserWithEmailAndPassword,
  getRedirectResult: vi.fn(async () => null),
  GoogleAuthProvider: class {
    setCustomParameters = vi.fn();
  },
  signOut: firebaseMocks.signOut,
  signInWithPopup: vi.fn(async () => ({
    user: { getIdToken: vi.fn(async () => "firebase-test-token") },
  })),
  signInWithRedirect: vi.fn(),
}));

describe("RegisterForm", () => {
  it("places Google registration below the email registration button", async () => {
    render(<RegisterForm />);

    const emailButton = screen.getByRole("button", { name: "Đăng ký" });
    const googleButton = await screen.findByRole("button", {
      name: "Tiếp tục với Google",
    });
    expect(
      emailButton.compareDocumentPosition(googleButton) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    replace.mockReset();
    refresh.mockReset();
    setQueryData.mockReset();
    firebaseMocks.createUserWithEmailAndPassword.mockReset();
    firebaseMocks.signOut.mockReset();
    firebaseMocks.signOut.mockResolvedValue(undefined);
  });

  it("explains the account purpose in clear production copy", () => {
    render(<RegisterForm />);

    expect(
      screen.getByText(
        "Tạo tài khoản để gửi hồ sơ, lưu bản nháp và theo dõi quá trình xử lý.",
      ),
    ).toBeDefined();
  });

  it("rejects mismatched passwords without a network request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@cnsgroup.vn",
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
    const user = {
      uid: "firebase-user-1",
      getIdToken: vi.fn(async () => "firebase-test-token"),
    };
    const fetchMock = vi.spyOn(globalThis, "fetch");
    firebaseMocks.createUserWithEmailAndPassword.mockResolvedValue({ user });
    const sendEmail = vi
      .spyOn(authApi, "sendFirebaseVerificationEmail")
      .mockResolvedValue({ message: "sent" });
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@cnsgroup.vn",
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
    expect(
      screen.getByText("Kiểm tra email để hoàn tất đăng ký"),
    ).toBeDefined();
    expect(
      screen.getByText(/Chúng tôi đã gửi liên kết xác minh tới/),
    ).toBeDefined();
    expect(screen.getByText("owner@cnsgroup.vn")).toBeDefined();
    expect(firebaseMocks.createUserWithEmailAndPassword).toHaveBeenCalledWith(
      expect.objectContaining({ languageCode: "vi" }),
      "owner@cnsgroup.vn",
      "correct horse battery staple",
    );
    expect(sendEmail).toHaveBeenCalledWith("firebase-test-token");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("explains how to resend when the account was created but email delivery fails", async () => {
    firebaseMocks.createUserWithEmailAndPassword.mockResolvedValue({
      user: {
        uid: "firebase-user-2",
        getIdToken: vi.fn(async () => "firebase-test-token"),
      },
    });
    vi.spyOn(authApi, "sendFirebaseVerificationEmail").mockRejectedValue(
      new Error("mail unavailable"),
    );
    render(<RegisterForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@cnsgroup.vn",
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

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Tài khoản đã được tạo nhưng chưa gửi được email xác minh",
    );
    expect(firebaseMocks.signOut).toHaveBeenCalledOnce();
  });

  it("does not ask new users to choose an account type", () => {
    render(<RegisterForm />);

    expect(
      screen.getByText(
        "Tạo tài khoản để gửi hồ sơ, lưu bản nháp và theo dõi quá trình xử lý.",
      ),
    ).toBeDefined();
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.queryByText("Cá nhân")).toBeNull();
    expect(screen.queryByText("Tổ chức")).toBeNull();
    expect(screen.queryByText(/nhân sự không đăng ký/i)).toBeNull();
  });

  it("starts Google signup with the public account intent and shows provider errors", async () => {
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
      await screen.findByRole("button", { name: "Tiếp tục với Google" }),
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
