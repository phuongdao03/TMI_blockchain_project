"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  createUserWithEmailAndPassword,
  sendEmailVerification,
  signOut,
} from "firebase/auth";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";
import { Button } from "@/components/ui/button";
import { registerSchema, type RegisterValues } from "@/lib/auth/schemas";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

export function RegisterForm() {
  const [submitError, setSubmitError] = useState<string>();
  const [accepted, setAccepted] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      const auth = getFirebaseAuth();
      const credential = await createUserWithEmailAndPassword(
        auth,
        values.email,
        values.password,
      );
      const continueUrl = new URL("/login", window.location.origin);
      try {
        await sendEmailVerification(credential.user, {
          url: continueUrl.toString(),
        });
      } finally {
        await signOut(auth);
      }
      setAccepted(true);
    } catch {
      setSubmitError(
        typeof navigator !== "undefined" && !navigator.onLine
          ? "Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại."
          : "Không thể đăng ký lúc này. Vui lòng thử lại.",
      );
    }
  });

  return (
    <AuthCard
      description="Đăng ký để lưu nội dung quan tâm và nhận những cập nhật mới từ chương trình."
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
          <GoogleOAuthButton accountType="PUBLIC_USER" />
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
