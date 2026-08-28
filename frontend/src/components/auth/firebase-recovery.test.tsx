import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

const firebaseMocks = vi.hoisted(() => ({
  confirmPasswordReset: vi.fn(),
  sendPasswordResetEmail: vi.fn(),
}));

vi.mock("@/lib/firebase/client", () => ({
  firebaseConfigured: () => true,
  getFirebaseAuth: () => ({ name: "firebase-auth" }),
}));

vi.mock("firebase/auth", () => ({
  confirmPasswordReset: firebaseMocks.confirmPasswordReset,
  sendPasswordResetEmail: firebaseMocks.sendPasswordResetEmail,
}));

describe("Firebase password recovery", () => {
  afterEach(() => {
    firebaseMocks.confirmPasswordReset.mockReset();
    firebaseMocks.sendPasswordResetEmail.mockReset();
  });

  it("requests a Firebase reset email and keeps the response generic", async () => {
    firebaseMocks.sendPasswordResetEmail.mockResolvedValue(undefined);
    render(<ForgotPasswordForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Gửi hướng dẫn" }),
    );

    const status = await screen.findByRole("status");
    expect(status.textContent).toContain("Hộp thư đến");
    expect(status.textContent).toContain("Spam/Thư rác");
    expect(status.textContent).not.toContain("Nếu địa chỉ tồn tại");
    expect(firebaseMocks.sendPasswordResetEmail).toHaveBeenCalledWith(
      { name: "firebase-auth" },
      "owner@tmigroup.vn",
      {
        handleCodeInApp: false,
        url: `${window.location.origin}/login`,
      },
    );
  });

  it("explains when password recovery is disabled in Firebase", async () => {
    firebaseMocks.sendPasswordResetEmail.mockRejectedValue({
      code: "auth/operation-not-allowed",
    });
    render(<ForgotPasswordForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "owner@tmigroup.vn",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Gửi hướng dẫn" }),
    );

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Chức năng khôi phục mật khẩu chưa được cấu hình",
    );
  });

  it("does not reveal whether an email exists", async () => {
    firebaseMocks.sendPasswordResetEmail.mockRejectedValue({
      code: "auth/user-not-found",
    });
    render(<ForgotPasswordForm />);

    await userEvent.type(
      screen.getByRole("textbox", { name: "Email" }),
      "missing@tmigroup.vn",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Gửi hướng dẫn" }),
    );

    expect(await screen.findByRole("status")).toBeDefined();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("confirms the one-time Firebase reset code without sending it to the backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch");
    firebaseMocks.confirmPasswordReset.mockResolvedValue(undefined);
    render(<ResetPasswordForm oobCode="firebase-one-time-code-123456789012" />);

    await userEvent.type(
      screen.getByLabelText("Mật khẩu mới"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu mới"),
      "correct horse battery staple",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Cập nhật mật khẩu" }),
    );

    expect(await screen.findByRole("status")).toBeDefined();
    expect(firebaseMocks.confirmPasswordReset).toHaveBeenCalledWith(
      { name: "firebase-auth" },
      "firebase-one-time-code-123456789012",
      "correct horse battery staple",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a safe message for an expired reset code", async () => {
    firebaseMocks.confirmPasswordReset.mockRejectedValue({
      code: "auth/expired-action-code",
      message: "firebase-secret-internal-detail",
    });
    render(<ResetPasswordForm oobCode="firebase-one-time-code-123456789012" />);

    await userEvent.type(
      screen.getByLabelText("Mật khẩu mới"),
      "correct horse battery staple",
    );
    await userEvent.type(
      screen.getByLabelText("Xác nhận mật khẩu mới"),
      "correct horse battery staple",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Cập nhật mật khẩu" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain(
      "Liên kết đặt lại mật khẩu không còn hiệu lực",
    );
    expect(alert.textContent).not.toContain("firebase-secret-internal-detail");
  });
});
