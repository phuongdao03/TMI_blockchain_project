"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { createUserWithEmailAndPassword, signOut } from "firebase/auth";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { FormField } from "@/components/auth/form-field";
import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";
import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/api/client";
import { registerSchema, type RegisterValues } from "@/lib/auth/schemas";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

export function RegisterForm() {
  const [submitError, setSubmitError] = useState<string>();
  const [acceptedEmail, setAcceptedEmail] = useState<string>();
  const [submitPhase, setSubmitPhase] = useState<"creating" | "sending">();
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
    setSubmitPhase("creating");
    let accountCreated = false;
    try {
      // Give the browser a frame to show progress before Firebase initializes.
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      const auth = getFirebaseAuth();
      auth.languageCode = "vi";
      const credential = await createUserWithEmailAndPassword(
        auth,
        values.email,
        values.password,
      );
      accountCreated = true;
      setSubmitPhase("sending");
      try {
        await authApi.sendFirebaseVerificationEmail(
          await credential.user.getIdToken(),
        );
      } finally {
        await signOut(auth).catch(() => undefined);
      }
      setAcceptedEmail(values.email.trim());
    } catch {
      setSubmitError(
        accountCreated
          ? "Tài khoản đã được tạo nhưng chưa gửi được email xác minh. Hãy đăng nhập bằng email và mật khẩu vừa tạo để gửi lại liên kết."
          : typeof navigator !== "undefined" && !navigator.onLine
            ? "Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại."
            : "Không thể đăng ký lúc này. Vui lòng thử lại.",
      );
    } finally {
      setSubmitPhase(undefined);
    }
  });

  return (
    <AuthCard
      description="Tạo tài khoản để gửi hồ sơ, lưu bản nháp và theo dõi quá trình xử lý."
      footer={
        <>
          Đã có tài khoản? <AuthLink href="/login">Đăng nhập</AuthLink>
        </>
      }
      title="Tạo tài khoản"
    >
      {acceptedEmail ? (
        <div
          className="rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          <p className="font-semibold">Kiểm tra email để hoàn tất đăng ký</p>
          <p className="mt-2">
            Chúng tôi đã gửi liên kết xác minh tới{" "}
            <strong>{acceptedEmail}</strong>. Hãy mở Hộp thư đến hoặc thư rác,
            chọn “Xác minh email”, rồi quay lại đăng nhập.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
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
            <Button
              className="auth-submit-button w-full"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="auth-activity-spinner size-5"
                />
              ) : null}
              {submitPhase === "sending"
                ? "Đang gửi email xác minh…"
                : isSubmitting
                  ? "Đang tạo tài khoản…"
                  : "Đăng ký"}
            </Button>
            {isSubmitting ? (
              <div className="auth-submit-progress" role="status">
                <span>
                  {submitPhase === "sending"
                    ? "Tài khoản đã tạo. Đang gửi thư xác minh…"
                    : "Đang tạo tài khoản của bạn…"}
                </span>
                <span
                  aria-hidden="true"
                  className="auth-submit-progress__track"
                >
                  <span className="auth-submit-progress__bar" />
                </span>
              </div>
            ) : null}
          </form>
          <div aria-hidden="true" className="flex items-center gap-3">
            <span className="h-px flex-1 bg-white/10" />
            <span className="font-mono text-[0.6rem] tracking-[0.12em] text-[#6f6d6c] uppercase">
              Hoặc tiếp tục với Google
            </span>
            <span className="h-px flex-1 bg-white/10" />
          </div>
          <GoogleOAuthButton accountType="PUBLIC_USER" />
        </div>
      )}
    </AuthCard>
  );
}
