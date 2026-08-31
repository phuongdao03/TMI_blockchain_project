"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import {
  getMultiFactorResolver,
  signInWithEmailAndPassword,
  TotpMultiFactorGenerator,
  type MultiFactorError,
  type MultiFactorResolver,
  type User,
} from "firebase/auth";
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
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

function safeDestination(value: string | undefined, fallback: string): string {
  return value?.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

export function LoginForm({ next }: { next?: string }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string>();
  const [mfaResolver, setMfaResolver] = useState<MultiFactorResolver>();
  const [verificationCode, setVerificationCode] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function finishSignIn(user: User) {
    const idToken = await user.getIdToken(true);
    const result = await authApi.exchangeFirebaseToken(
      idToken,
      "PUBLIC_USER",
      next,
    );
    queryClient.setQueryData(["auth", "me"], result.user);
    router.replace(
      safeDestination(
        next,
        resolveDefaultWorkspace(result.user.roles, result.user.permissions),
      ),
    );
    router.refresh();
  }

  function loginErrorMessage(error: unknown): string {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      return "Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại.";
    }
    const code = (error as { code?: string } | null)?.code;
    if (
      [
        "auth/invalid-credential",
        "auth/user-not-found",
        "auth/wrong-password",
      ].includes(code ?? "")
    ) {
      return "Email hoặc mật khẩu chưa đúng. Vui lòng kiểm tra lại.";
    }
    if (code === "auth/too-many-requests") {
      return "Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.";
    }
    if (code === "auth/operation-not-allowed") {
      return "Đăng nhập bằng email chưa được cấu hình. Vui lòng liên hệ quản trị hệ thống.";
    }
    if (
      [
        "auth/invalid-api-key",
        "auth/app-not-authorized",
        "auth/unauthorized-domain",
      ].includes(code ?? "") ||
      (error as Error | null)?.message === "FIREBASE_CLIENT_NOT_CONFIGURED"
    ) {
      return "Dịch vụ đăng nhập chưa được cấu hình đúng. Vui lòng liên hệ quản trị hệ thống.";
    }
    if (code === "auth/network-request-failed") {
      return "Không thể kết nối dịch vụ đăng nhập. Vui lòng kiểm tra mạng rồi thử lại.";
    }
    if (error instanceof ApiError && error.status === 429) {
      return "Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.";
    }
    if (
      error instanceof ApiError &&
      error.code === "OAUTH_ACCOUNT_LINK_REQUIRED"
    ) {
      return "Tài khoản chưa được liên kết hoàn tất. Vui lòng liên hệ quản trị hệ thống.";
    }
    if (
      error instanceof ApiError &&
      ["OAUTH_IDENTITY_INVALID", "ACCOUNT_INACTIVE"].includes(error.code)
    ) {
      return "Tài khoản chưa hoạt động hoặc quyền truy cập không còn hiệu lực. Vui lòng liên hệ quản trị hệ thống.";
    }
    if (error instanceof ApiError && error.code === "STAFF_MFA_REQUIRED") {
      return "Tài khoản quản trị cần hoàn tất xác thực bảo mật trước khi đăng nhập.";
    }
    if (error instanceof ApiError && error.status >= 500) {
      return "Dịch vụ tài khoản đang tạm gián đoạn. Vui lòng thử lại sau ít phút.";
    }
    return "Không thể đăng nhập lúc này. Vui lòng thử lại.";
  }

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      const credential = await signInWithEmailAndPassword(
        getFirebaseAuth(),
        values.email,
        values.password,
      );
      await finishSignIn(credential.user);
    } catch (error) {
      if (
        (error as { code?: string } | null)?.code ===
        "auth/multi-factor-auth-required"
      ) {
        setMfaResolver(
          getMultiFactorResolver(getFirebaseAuth(), error as MultiFactorError),
        );
        return;
      }
      setSubmitError(loginErrorMessage(error));
    }
  });

  async function verifySecondFactor() {
    if (!mfaResolver || !/^\d{6}$/.test(verificationCode)) return;
    setSubmitError(undefined);
    try {
      const hint = mfaResolver.hints.find(
        (item) => item.factorId === TotpMultiFactorGenerator.FACTOR_ID,
      );
      if (!hint) throw new Error("TOTP_FACTOR_NOT_FOUND");
      const assertion = TotpMultiFactorGenerator.assertionForSignIn(
        hint.uid,
        verificationCode,
      );
      const credential = await mfaResolver.resolveSignIn(assertion);
      await finishSignIn(credential.user);
    } catch {
      setSubmitError(
        "Mã xác minh không đúng hoặc đã hết hạn. Vui lòng thử lại.",
      );
    }
  }

  return (
    <AuthCard
      description="Truy cập không gian hồ sơ để theo dõi tiến trình, phản hồi và chứng thư của bạn."
      footer={
        <>
          Chưa có tài khoản? <AuthLink href="/register">Tạo tài khoản</AuthLink>
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
          {mfaResolver ? (
            <div className="space-y-3 rounded-lg border border-[#F6C515]/30 bg-[#201d16] p-4">
              <label
                className="block text-sm font-semibold"
                htmlFor="email-mfa-code"
              >
                Mã 6 số từ ứng dụng xác thực
              </label>
              <input
                autoComplete="one-time-code"
                className="min-h-12 w-full rounded-md border border-white/20 bg-[#111] px-3 text-center font-mono text-lg tracking-[0.3em] text-white"
                id="email-mfa-code"
                inputMode="numeric"
                maxLength={6}
                onChange={(event) =>
                  setVerificationCode(event.target.value.replace(/\D/g, ""))
                }
                value={verificationCode}
              />
              <Button
                className="w-full"
                disabled={verificationCode.length !== 6}
                onClick={() => void verifySecondFactor()}
                type="button"
              >
                Xác nhận mã
              </Button>
            </div>
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
          <Button
            className="w-full"
            disabled={isSubmitting || Boolean(mfaResolver)}
            type="submit"
          >
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-5 animate-spin"
              />
            ) : null}
            {isSubmitting ? "Đang đăng nhập…" : "Đăng nhập"}
          </Button>
        </form>
      </div>
    </AuthCard>
  );
}
