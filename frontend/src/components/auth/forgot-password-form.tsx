"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { sendPasswordResetEmail } from "firebase/auth";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import {
  forgotPasswordSchema,
  type ForgotPasswordValues,
} from "@/lib/auth/schemas";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

export function ForgotPasswordForm() {
  const [submitError, setSubmitError] = useState<string>();
  const [accepted, setAccepted] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = handleSubmit(async ({ email }) => {
    setSubmitError(undefined);
    try {
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      await sendPasswordResetEmail(getFirebaseAuth(), email, {
        handleCodeInApp: false,
        url: `${window.location.origin}/login`,
      });
      setAccepted(true);
    } catch (error) {
      const code = (error as { code?: string } | null)?.code;
      if (code === "auth/user-not-found") {
        setAccepted(true);
        return;
      }
      if (code === "auth/too-many-requests") {
        setSubmitError(
          "Bạn đã gửi quá nhiều yêu cầu. Vui lòng chờ một lát rồi thử lại.",
        );
        return;
      }
      if (code === "auth/operation-not-allowed") {
        setSubmitError(
          "Chức năng khôi phục mật khẩu chưa được cấu hình. Vui lòng liên hệ bộ phận hỗ trợ.",
        );
        return;
      }
      if (
        [
          "auth/unauthorized-continue-uri",
          "auth/unauthorized-domain",
          "auth/invalid-api-key",
          "auth/app-not-authorized",
        ].includes(code ?? "") ||
        (error as Error | null)?.message === "FIREBASE_CLIENT_NOT_CONFIGURED"
      ) {
        setSubmitError(
          "Dịch vụ khôi phục tài khoản chưa sẵn sàng. Vui lòng liên hệ bộ phận hỗ trợ.",
        );
        return;
      }
      setSubmitError(
        typeof navigator !== "undefined" && !navigator.onLine
          ? "Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại."
          : "Không thể gửi yêu cầu lúc này. Vui lòng thử lại.",
      );
    }
  });

  return (
    <AuthCard
      description="Nhập email đã dùng để đăng ký. Firebase sẽ gửi liên kết bảo mật để bạn đặt mật khẩu mới."
      footer={<AuthLink href="/login">Quay lại đăng nhập</AuthLink>}
      title="Quên mật khẩu"
    >
      {accepted ? (
        <div
          className="rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          Yêu cầu đặt lại mật khẩu đã được tiếp nhận. Vui lòng kiểm tra Hộp thư
          đến và mục Spam/Thư rác để mở liên kết đổi mật khẩu. Nếu chưa nhận
          được email sau vài phút, hãy thử gửi lại yêu cầu.
        </div>
      ) : (
        <form className="space-y-5" noValidate onSubmit={onSubmit}>
          {submitError ? (
            <p className="text-sm font-medium text-error" role="alert">
              {submitError}
            </p>
          ) : null}
          <FormField
            autoComplete="email"
            error={errors.email?.message}
            label="Email"
            type="email"
            {...register("email")}
          />
          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-5 animate-spin"
              />
            ) : null}
            {isSubmitting ? "Đang gửi…" : "Gửi hướng dẫn"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
