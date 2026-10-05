"use client";

import { applyActionCode } from "firebase/auth";
import { BadgeCheck, LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

type EmailActionMode = "verifyEmail" | "recoverEmail" | "verifyAndChangeEmail";

function isEmailActionMode(value: string): value is EmailActionMode {
  return ["verifyEmail", "recoverEmail", "verifyAndChangeEmail"].includes(
    value,
  );
}

export function FirebaseEmailAction({
  mode,
  oobCode,
}: {
  mode: string;
  oobCode: string;
}) {
  const [state, setState] = useState<"pending" | "success" | "error">(
    "pending",
  );
  const actionRequest = useRef<Promise<void> | null>(null);

  useEffect(() => {
    if (!oobCode || !isEmailActionMode(mode)) return;
    let active = true;
    if (!actionRequest.current) {
      actionRequest.current = (async () => {
        if (!firebaseConfigured())
          throw new Error("FIREBASE_CLIENT_NOT_CONFIGURED");
        const auth = getFirebaseAuth();
        auth.languageCode = "vi";
        await applyActionCode(auth, oobCode);
      })();
    }
    void actionRequest.current.then(
      () => {
        if (active) setState("success");
      },
      () => {
        if (active) setState("error");
      },
    );
    return () => {
      active = false;
    };
  }, [mode, oobCode]);

  if (mode === "resetPassword" && oobCode) {
    return <ResetPasswordForm oobCode={oobCode} />;
  }

  const supported = isEmailActionMode(mode) && Boolean(oobCode);
  const title =
    mode === "recoverEmail"
      ? "Khôi phục email"
      : mode === "verifyAndChangeEmail"
        ? "Xác nhận email mới"
        : "Xác minh email";

  return (
    <AuthCard
      description="Hoàn tất yêu cầu bảo mật cho tài khoản Đề cử Tinh Hoa Việt."
      footer={<AuthLink href="/login">Đến trang đăng nhập</AuthLink>}
      title={title}
    >
      {!supported || state === "error" ? (
        <div
          className="rounded-lg border border-error bg-primary-50 p-4 text-sm text-error"
          role="alert"
        >
          Liên kết không hợp lệ hoặc đã hết hạn. Hãy đăng nhập để gửi lại yêu
          cầu.
        </div>
      ) : state === "success" ? (
        <div
          className="flex gap-3 rounded-lg border border-success bg-green-50 p-4 text-sm text-green-800"
          role="status"
        >
          <BadgeCheck aria-hidden="true" className="size-5 shrink-0" />
          {mode === "recoverEmail"
            ? "Địa chỉ email trước đó đã được khôi phục. Bạn có thể đăng nhập lại."
            : mode === "verifyAndChangeEmail"
              ? "Địa chỉ email mới đã được xác nhận. Bạn có thể đăng nhập lại."
              : "Email đã được xác minh thành công. Bạn có thể đăng nhập ngay."}
        </div>
      ) : (
        <div className="flex items-center gap-3 text-sm" role="status">
          <LoaderCircle
            aria-hidden="true"
            className="auth-activity-spinner size-5"
          />
          Đang xác minh liên kết bảo mật…
        </div>
      )}
    </AuthCard>
  );
}
