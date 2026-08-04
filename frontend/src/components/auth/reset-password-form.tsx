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
  resetPasswordSchema,
  type ResetPasswordValues,
} from "@/lib/auth/schemas";

export function ResetPasswordForm({ token }: { token: string }) {
  const [submitError, setSubmitError] = useState<string>();
  const [completed, setCompleted] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token, newPassword: "", confirmPassword: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      await authApi.resetPassword(values.token, values.newPassword);
      setCompleted(true);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Không thể đặt lại mật khẩu lúc này.",
      );
    }
  });

  return (
    <AuthCard
      description="Tạo mật khẩu mới. Mọi phiên đăng nhập cũ sẽ bị thu hồi."
      footer={<AuthLink href="/login">Quay lại đăng nhập</AuthLink>}
      title="Đặt lại mật khẩu"
    >
      {completed ? (
        <div
          className="rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          Mật khẩu đã được cập nhật. Bạn có thể đăng nhập lại.
        </div>
      ) : (
        <form className="space-y-5" noValidate onSubmit={onSubmit}>
          {errors.token ? (
            <p className="text-sm font-medium text-error" role="alert">
              {errors.token.message}
            </p>
          ) : null}
          {submitError ? (
            <p className="text-sm font-medium text-error" role="alert">
              {submitError}
            </p>
          ) : null}
          <FormField
            autoComplete="new-password"
            error={errors.newPassword?.message}
            hint="Dùng ít nhất 12 ký tự."
            label="Mật khẩu mới"
            type="password"
            {...register("newPassword")}
          />
          <FormField
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            label="Xác nhận mật khẩu mới"
            type="password"
            {...register("confirmPassword")}
          />
          <Button className="w-full" disabled={isSubmitting} type="submit">
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-5 animate-spin"
              />
            ) : null}
            {isSubmitting ? "Đang cập nhật…" : "Cập nhật mật khẩu"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
