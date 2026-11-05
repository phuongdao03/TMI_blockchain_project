"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { signInWithEmailAndPassword, signOut, type User } from "firebase/auth";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { AuthNavigationStatus } from "@/components/auth/auth-navigation-status";
import { FormField } from "@/components/auth/form-field";
import { GoogleOAuthButton } from "@/components/auth/google-oauth-button";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import type { AccountType, AuthUser } from "@/lib/api/types";
import { loginSchema, type LoginValues } from "@/lib/auth/schemas";
import { safeLocalDestination } from "@/lib/auth/safe-destination";
import { broadcastAuthSessionChange } from "@/lib/auth/session-sync";
import { deliverVerificationEmail } from "@/lib/auth/verification-email";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";
import { ensureReferralAttribution } from "@/lib/auth/referral-attribution";

export function LoginForm({
  next,
  accountType = "PUBLIC_USER",
}: {
  next?: string;
  accountType?: AccountType;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string>();
  const [navigating, setNavigating] = useState(false);
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
    const destination = safeLocalDestination(next, "/workspace");
    const referral = await ensureReferralAttribution();
    const result = await authApi.exchangeFirebaseToken(
      idToken,
      accountType,
      destination,
      referral
        ? {
            referralCode: referral.referralCode,
            referralClickId: referral.clickId,
          }
        : undefined,
    );
    enterWorkspace(result.user, destination);
  }

  function enterWorkspace(
    user: AuthUser,
    destination = safeLocalDestination(next, "/workspace"),
  ) {
    queryClient.setQueryData(["auth", "me"], user);
    broadcastAuthSessionChange();
    setNavigating(true);
    router.replace(destination);
    router.refresh();
  }

  function loginErrorMessage(error: unknown): string {
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      error.code !== "OAUTH_IDENTITY_INVALID" &&
      error.code !== "ACCOUNT_INACTIVE"
    )
      return "Email/tên đăng nhập hoặc mật khẩu chưa đúng.";
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
      return "Đăng nhập bằng email hiện chưa khả dụng. Vui lòng liên hệ bộ phận hỗ trợ.";
    }
    if (
      [
        "auth/invalid-api-key",
        "auth/app-not-authorized",
        "auth/unauthorized-domain",
      ].includes(code ?? "") ||
      (error as Error | null)?.message === "FIREBASE_CLIENT_NOT_CONFIGURED"
    ) {
      return "Chưa thể đăng nhập bằng email lúc này. Vui lòng liên hệ bộ phận hỗ trợ.";
    }
    if (code === "auth/network-request-failed") {
      return "Không thể kết nối để đăng nhập. Hãy kiểm tra mạng rồi thử lại.";
    }
    if (error instanceof ApiError && error.status === 429) {
      return "Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.";
    }
    if (
      error instanceof ApiError &&
      error.code === "OAUTH_ACCOUNT_LINK_REQUIRED"
    ) {
      return "Tài khoản này chưa thể dùng để đăng nhập. Vui lòng liên hệ bộ phận hỗ trợ.";
    }
    if (error instanceof ApiError && error.code === "OAUTH_IDENTITY_INVALID") {
      return "Không xác minh được tài khoản. Hãy đăng xuất rồi đăng nhập lại. Nếu vẫn gặp lỗi, liên hệ bộ phận hỗ trợ.";
    }
    if (error instanceof ApiError && error.code === "ACCOUNT_INACTIVE") {
      return "Tài khoản chưa được kích hoạt hoặc quyền truy cập đã hết hiệu lực. Vui lòng liên hệ bộ phận hỗ trợ.";
    }
    if (error instanceof ApiError && error.status >= 500) {
      return "Đăng nhập đang tạm gián đoạn. Hãy thử lại sau.";
    }
    return "Không thể đăng nhập lúc này. Vui lòng thử lại.";
  }

  const onSubmit = handleSubmit(async (values) => {
    setSubmitError(undefined);
    try {
      if (!values.email.includes("@")) {
        const result = await authApi.loginWithUsername(
          values.email,
          values.password,
        );
        enterWorkspace(result.user);
        return;
      }
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      const auth = getFirebaseAuth();
      auth.languageCode = "vi";
      let credential;
      try {
        credential = await signInWithEmailAndPassword(
          auth,
          values.email,
          values.password,
        );
      } catch (error) {
        const code = (error as { code?: string } | null)?.code;
        if (
          ![
            "auth/invalid-credential",
            "auth/user-not-found",
            "auth/wrong-password",
          ].includes(code ?? "")
        )
          throw error;
        const result = await authApi.loginWithEmail(
          values.email,
          values.password,
        );
        enterWorkspace(result.user);
        return;
      }
      if (!credential.user.emailVerified) {
        try {
          await deliverVerificationEmail(credential.user);
          setSubmitError(
            "Email chưa được xác minh. Chúng tôi đã gửi lại liên kết xác minh; hãy mở email rồi đăng nhập lại.",
          );
        } catch {
          setSubmitError(
            "Email chưa được xác minh. Chưa thể gửi lại liên kết lúc này; vui lòng thử lại sau.",
          );
        } finally {
          await signOut(auth).catch(() => undefined);
        }
        return;
      }
      await finishSignIn(credential.user);
    } catch (error) {
      setNavigating(false);
      setSubmitError(loginErrorMessage(error));
    }
  });

  return (
    <AuthCard
      description="Đăng nhập để theo dõi hồ sơ, phản hồi yêu cầu bổ sung và xem bằng xác lập."
      footer={
        <>
          Chưa có tài khoản?{" "}
          <AuthLink
            href={
              next
                ? `/register?next=${encodeURIComponent(safeLocalDestination(next, "/workspace"))}`
                : "/register"
            }
          >
            Tạo tài khoản
          </AuthLink>
        </>
      }
      title="Đăng nhập"
    >
      {navigating ? <AuthNavigationStatus /> : null}
      <div className="space-y-5">
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
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            error={errors.email?.message}
            label="Email hoặc tên đăng nhập"
            hint="Dùng email hoặc tên đăng nhập đã đăng ký. Tên hiển thị không dùng để đăng nhập."
            type="text"
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
            {isSubmitting ? "Đang đăng nhập…" : "Đăng nhập"}
          </Button>
        </form>
        <div aria-hidden="true" className="flex items-center gap-3">
          <span className="h-px flex-1 bg-white/10" />
          <span className="font-mono text-[0.6rem] tracking-[0.12em] text-[#6f6d6c] uppercase">
            Hoặc tiếp tục với Google
          </span>
          <span className="h-px flex-1 bg-white/10" />
        </div>
        <GoogleOAuthButton accountType="PUBLIC_USER" next={next} />
      </div>
    </AuthCard>
  );
}
