"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import { registerSchema, type RegisterValues } from "@/lib/auth/schemas";

export function RegisterForm() {
  const [submitError, setSubmitError] = useState<string>();
  const [accepted, setAccepted] = useState(false);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      accountType: "PUBLIC_USER",
    },
  });
  const accountType = useWatch({ control, name: "accountType" });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      await authApi.register(values.email, values.password, values.accountType);
      setAccepted(true);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Không thể đăng ký lúc này. Vui lòng thử lại.",
      );
    }
  });

  return (
    <AuthCard
      description="Chọn đúng mục đích sử dụng; quyền và không gian làm việc sẽ theo tài khoản của bạn."
      footer={
        <>
          Đã có tài khoản? <AuthLink href="/login">Đăng nhập</AuthLink>
        </>
      }
      title="Tạo tài khoản"
    >
      {accepted ? (
        <div
          className="rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          Nếu địa chỉ có thể đăng ký, hướng dẫn xác minh đã được gửi. Vui lòng
          kiểm tra hộp thư.
        </div>
      ) : (
        <form className="space-y-5" noValidate onSubmit={onSubmit}>
          {submitError ? (
            <p className="text-sm font-medium text-error" role="alert">
              {submitError}
            </p>
          ) : null}
          <fieldset>
            <legend className="mb-3 font-mono text-[0.65rem] font-medium tracking-[0.1em] text-[#e7bdb7] uppercase">
              Bạn muốn sử dụng nền tảng theo cách nào
            </legend>
            <div className="grid gap-2 sm:grid-cols-3">
              {(
                [
                  [
                    "PUBLIC_USER",
                    "Khám phá công khai",
                    "Tra cứu, xác minh và theo dõi tài sản công khai",
                  ],
                  [
                    "INDIVIDUAL_APPLICANT",
                    "Cá nhân",
                    "Quản lý hồ sơ tài sản của bạn",
                  ],
                  [
                    "ORGANIZATION_APPLICANT",
                    "Tổ chức",
                    "Đại diện đơn vị và cộng tác với thành viên",
                  ],
                ] as const
              ).map(([value, label, description]) => (
                <label
                  className="cursor-pointer rounded-md border border-white/8 bg-[#131313] p-3.5 transition-colors hover:border-[#ad8883] has-[:checked]:border-[#ff5545] has-[:checked]:bg-[#2a1d1b]"
                  key={value}
                >
                  <span className="flex items-start gap-3">
                    <input
                      className="mt-1 accent-primary-600"
                      type="radio"
                      value={value}
                      {...register("accountType")}
                    />
                    <span>
                      <span className="block text-sm font-bold text-[#e5e2e1]">
                        {label}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-[#929090]">
                        {description}
                      </span>
                    </span>
                  </span>
                </label>
              ))}
            </div>
            {errors.accountType ? (
              <p className="mt-2 text-sm text-error">
                {errors.accountType.message}
              </p>
            ) : null}
          </fieldset>
          <GoogleOAuthButton accountType={accountType} />
          <div aria-hidden="true" className="flex items-center gap-3">
            <span className="h-px flex-1 bg-white/10" />
            <span className="font-mono text-[0.6rem] tracking-[0.12em] text-[#6f6d6c] uppercase">
              Hoặc đăng ký bằng email
            </span>
            <span className="h-px flex-1 bg-white/10" />
          </div>
          <FormField
            autoComplete="email"
            error={errors.email?.message}
            label="Email"
            type="email"
            {...register("email")}
          />
          <FormField
            autoComplete="new-password"
            error={errors.password?.message}
            hint="Dùng ít nhất 12 ký tự."
            label="Mật khẩu"
            type="password"
            {...register("password")}
          />
          <FormField
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            label="Xác nhận mật khẩu"
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
            {isSubmitting ? "Đang tạo tài khoản…" : "Đăng ký"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
