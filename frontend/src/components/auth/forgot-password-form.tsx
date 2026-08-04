"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import {
  forgotPasswordSchema,
  type ForgotPasswordValues,
} from "@/lib/auth/schemas";

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
      await authApi.forgotPassword(email);
      setAccepted(true);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Không thể gửi yêu cầu lúc này. Vui lòng thử lại.",
      );
    }
  });

  return (
    <AuthCard
      description="Nhập email của bạn. Phản hồi luôn giống nhau để bảo vệ tài khoản."
      footer={<AuthLink href="/login">Quay lại đăng nhập</AuthLink>}
      title="Quên mật khẩu"
    >
      {accepted ? (
        <div
          className="rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          Nếu địa chỉ tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi.
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
