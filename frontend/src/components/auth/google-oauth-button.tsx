"use client";

import { useQueryClient } from "@tanstack/react-query";
import { GoogleAuthProvider, signInWithPopup, type User } from "firebase/auth";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, authApi } from "@/lib/api/client";
import { resolveDefaultWorkspace } from "@/lib/auth/role-workspaces";
import { getFirebaseAuth, firebaseConfigured } from "@/lib/firebase/client";
import type { AccountType } from "@/lib/api/types";

function safeDestination(value: string | undefined, fallback: string): string {
  return value?.startsWith("/") && !value.startsWith("//") ? value : fallback;
}

function oauthErrorMessage(error: unknown): string {
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    return "Bạn đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi thử lại.";
  }
  if (
    error instanceof Error &&
    error.message === "FIREBASE_CLIENT_NOT_CONFIGURED"
  ) {
    return "Đăng nhập Google đang được cấu hình. Bạn có thể dùng email và mật khẩu trong lúc này.";
  }
  if (error instanceof ApiError) {
    if (error.code === "OAUTH_RATE_LIMITED")
      return "Bạn đã thử quá nhiều lần. Vui lòng chờ một lát rồi thử lại.";
    if (error.code === "OAUTH_IDENTITY_INVALID")
      return "Tài khoản Google chưa được xác minh. Vui lòng chọn tài khoản khác.";
    if (error.code === "OAUTH_PROVIDER_UNAVAILABLE")
      return "Đăng nhập Google đang tạm thời gián đoạn. Vui lòng thử lại sau.";
    if (error.code === "OAUTH_ACCOUNT_LINK_REQUIRED")
      return "Email này đã có tài khoản. Hãy đăng nhập bằng email và mật khẩu trước.";
    return "Không thể hoàn tất đăng nhập lúc này. Vui lòng thử lại.";
  }
  const code = (error as { code?: string } | null)?.code;
  if (code === "auth/popup-closed-by-user")
    return "Bạn đã đóng cửa sổ đăng nhập Google.";
  if (code === "auth/popup-blocked")
    return "Trình duyệt đã chặn cửa sổ đăng nhập. Hãy cho phép popup rồi thử lại.";
  if (code === "auth/unauthorized-domain")
    return "Tên miền hiện tại chưa được cho phép đăng nhập Google.";
  return "Không thể kết nối Google lúc này. Vui lòng thử lại.";
}

export function GoogleOAuthButton({
  accountType,
  next,
  label = "Tiếp tục với Google",
}: {
  accountType: AccountType;
  next?: string;
  label?: string;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string>();

  async function finishSignIn(user: User) {
    const idToken = await user.getIdToken(true);
    const result = await authApi.exchangeFirebaseToken(
      idToken,
      accountType,
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

  async function startGoogleOAuth() {
    setError(undefined);
    setIsPending(true);
    try {
      if (!firebaseConfigured())
        throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
      const credential = await signInWithPopup(
        getFirebaseAuth(),
        new GoogleAuthProvider(),
      );
      await finishSignIn(credential.user);
    } catch (cause) {
      setError(oauthErrorMessage(cause));
      setIsPending(false);
    }
  }

  return (
    <div className="space-y-3">
      {error ? (
        <p
          className="rounded-md border border-[#ff8d82]/35 bg-[#3a1b19] px-3.5 py-3 text-sm font-medium text-[#ffb4aa]"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <button
        className="auth-google-button flex min-h-12 w-full items-center justify-center gap-3 rounded-md border border-[#ad8883]/45 bg-[#171717] px-4 text-sm font-bold text-[#e5e2e1] transition-colors hover:border-[#ffb4aa] hover:bg-[#242222] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#ffb4aa] disabled:pointer-events-none disabled:opacity-60"
        disabled={isPending}
        onClick={startGoogleOAuth}
        type="button"
      >
        {isPending ? (
          <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
        ) : (
          <span
            aria-hidden="true"
            className="grid size-5 place-items-center rounded-sm bg-[#e5e2e1] text-xs font-black text-[#242222]"
          >
            G
          </span>
        )}
        {isPending ? "Đang kết nối Google…" : label}
      </button>
    </div>
  );
}
