"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import { loginSchema, type LoginValues } from "@/lib/auth/schemas";
import { resolveDefaultWorkspace } from "@/lib/auth/role-workspaces";

function safeDestination(value: string | undefined, fallback: string): string {
  return value?.startsWith("/") && !value.startsWith("//")
    ? value
    : fallback;
}

export function LoginForm({ next }: { next?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string>();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      const result = await authApi.login(
        values.email,
        values.password,
        "Trình duyệt web",
      );
      queryClient.setQueryData(["auth", "me"], result.user);
      router.replace(safeDestination(next, resolveDefaultWorkspace(result.user.roles)));
      router.refresh();
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Không thể đăng nhập lúc này. Vui lòng thử lại.",
      );
    }
  });

  return (
    <AuthCard
      description="Truy cập hồ sơ và quản lý chứng thư tài sản số của bạn."
      footer={
        <>
          Chưa có tài khoản? <AuthLink href="/register">Đăng ký</AuthLink>
        </>
      }
      title="Đăng nhập"
    >
      <div className="space-y-5">
        <GoogleOAuthButton accountType="PUBLIC_USER" next={next} />
        <div aria-hidden="true" className="flex items-center gap-3">
          <span className="h-px flex-1 bg-white/10" />
          <span className="font-mono text-[0.6rem] tracking-[0.12em] text-[#6f6d6c] uppercase">
            Hoặc dùng email
          </span>
          <span className="h-px flex-1 bg-white/10" />
        </div>
        <form className="space-y-5" noValidate onSubmit={onSubmit}>
        {submitError ? (
          <p
            className="rounded-lg border border-error bg-primary-50 p-3 text-sm font-medium text-error"
            role="alert"
          >
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
        <div className="space-y-2">
          <FormField
            autoComplete="current-password"
            error={errors.password?.message}
            label="Mật khẩu"
            type="password"
            {...register("password")}
          />
          <div className="text-right">
            <AuthLink href="/forgot-password">Quên mật khẩu?</AuthLink>
          </div>
        </div>
        <Button className="w-full" disabled={isSubmitting} type="submit">
          {isSubmitting ? (
            <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          ) : null}
          {isSubmitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </Button>
        </form>
      </div>
    </AuthCard>
  );
}
