"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import { tokenSchema, type TokenValues } from "@/lib/auth/schemas";

export function VerifyEmailForm({ token }: { token: string }) {
  const [submitError, setSubmitError] = useState<string>();
  const [verified, setVerified] = useState(false);
  const {
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<TokenValues>({
    resolver: zodResolver(tokenSchema),
    defaultValues: { token },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      await authApi.verifyEmail(values.token);
      setVerified(true);
    } catch (error) {
      setSubmitError(
        error instanceof ApiError
          ? error.message
          : "Không thể xác minh email lúc này.",
      );
    }
  });

  return (
    <AuthCard
      description="Xác nhận địa chỉ email trước khi đăng nhập."
      footer={<AuthLink href="/login">Đến trang đăng nhập</AuthLink>}
      title="Xác minh email"
    >
      {verified ? (
        <div
          className="flex gap-3 rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          <BadgeCheck aria-hidden="true" className="size-5 shrink-0" />
          Email đã được xác minh thành công.
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
          <Button
            className="w-full"
            disabled={isSubmitting || Boolean(errors.token)}
            type="submit"
          >
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-5 animate-spin"
              />
            ) : null}
            {isSubmitting ? "Đang xác minh…" : "Xác minh email"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
