"use client";

import {
  GoogleAuthProvider,
  TotpMultiFactorGenerator,
  multiFactor,
  signInWithPopup,
  signOut,
  type TotpSecret,
} from "firebase/auth";
import { LoaderCircle, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

export function StaffInvitationForm({ token }: { token?: string }) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const [totpSecret, setTotpSecret] = useState<TotpSecret>();
  const [verificationCode, setVerificationCode] = useState("");
  const validToken = typeof token === "string" && token.length >= 32;

  async function acceptInvitation() {
    if (!validToken) return;
    setIsSubmitting(true);
    setError(undefined);
    try {
      if (!firebaseConfigured()) {
        throw new Error("Firebase is not configured");
      }
      const credential = await signInWithPopup(
        getFirebaseAuth(),
        new GoogleAuthProvider(),
      );
      const idToken = await credential.user.getIdToken(true);
      await authApi.acceptStaffInvitation(token, idToken);
      const session = await multiFactor(credential.user).getSession();
      setTotpSecret(await TotpMultiFactorGenerator.generateSecret(session));
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể xác nhận lời mời. Hãy dùng đúng email đã nhận thư và thử lại.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function enrollTotp() {
    const user = getFirebaseAuth().currentUser;
    if (!user || !totpSecret || !/^\d{6}$/.test(verificationCode)) return;
    setIsSubmitting(true);
    setError(undefined);
    try {
      const assertion = TotpMultiFactorGenerator.assertionForEnrollment(
        totpSecret,
        verificationCode,
      );
      await multiFactor(user).enroll(assertion, "TMI Authenticator");
      await signOut(getFirebaseAuth());
      router.replace("/login?mfa=enrolled");
      router.refresh();
    } catch {
      setError("Mã xác minh không đúng hoặc đã hết hạn. Vui lòng thử lại.");
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard
      description="Xác nhận danh tính bằng đúng email đã nhận lời mời để bắt đầu công việc."
      footer={<AuthLink href="/login">Quay lại đăng nhập</AuthLink>}
      title="Tham gia đội ngũ TMI"
    >
      <div className="space-y-5">
        <div className="rounded-xl border border-white/10 bg-white/[0.035] p-4">
          <div className="flex items-start gap-3">
            <ShieldCheck
              aria-hidden="true"
              className="mt-0.5 size-5 text-[#F6C515]"
            />
            <div>
              <p className="text-sm font-semibold text-[#F6C515]">
                Lời mời được bảo vệ
              </p>
              <p className="mt-1 text-xs leading-5 text-[#aaa6a4]">
                Liên kết chỉ dùng một lần. Tài khoản chỉ được kích hoạt khi
                email đăng nhập trùng với địa chỉ người quản trị đã mời.
              </p>
            </div>
          </div>
        </div>
        {!validToken ? (
          <p
            className="rounded-lg border border-red-400/40 bg-red-950/30 p-3 text-sm text-red-200"
            role="alert"
          >
            Liên kết lời mời không hợp lệ hoặc không đầy đủ. Hãy yêu cầu người
            quản trị gửi lại lời mời mới.
          </p>
        ) : null}
        {error ? (
          <p
            className="rounded-lg border border-red-400/40 bg-red-950/30 p-3 text-sm text-red-200"
            role="alert"
          >
            {error}
          </p>
        ) : null}
        {totpSecret ? (
          <div className="space-y-4">
            <div className="rounded-lg border border-[#F6C515]/30 bg-[#201d16] p-4">
              <p className="text-sm font-semibold text-[#F6C515]">
                Thiết lập ứng dụng xác thực
              </p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5 text-[#aaa6a4]">
                <li>Mở Google Authenticator hoặc ứng dụng TOTP tương thích.</li>
                <li>Chọn nhập khóa thiết lập và dùng khóa bên dưới.</li>
                <li>Nhập mã 6 số ứng dụng vừa tạo để hoàn tất.</li>
              </ol>
              <code className="mt-3 block break-all rounded-md bg-black/40 p-3 text-sm text-white">
                {totpSecret.secretKey}
              </code>
            </div>
            <label className="block text-sm font-semibold" htmlFor="totp-code">
              Mã xác minh 6 số
            </label>
            <input
              autoComplete="one-time-code"
              className="min-h-12 w-full rounded-md border border-white/20 bg-[#111] px-3 text-center font-mono text-lg tracking-[0.3em] text-white outline-none focus:border-[#F6C515]"
              id="totp-code"
              inputMode="numeric"
              maxLength={6}
              onChange={(event) =>
                setVerificationCode(event.target.value.replace(/\D/g, ""))
              }
              value={verificationCode}
            />
            <Button
              className="w-full"
              disabled={isSubmitting || verificationCode.length !== 6}
              onClick={enrollTotp}
              type="button"
            >
              {isSubmitting ? "Đang kích hoạt…" : "Kích hoạt bảo vệ hai bước"}
            </Button>
          </div>
        ) : (
          <>
            <Button
              className="w-full"
              disabled={!validToken || isSubmitting}
              onClick={acceptInvitation}
              type="button"
            >
              {isSubmitting ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="size-5 animate-spin"
                />
              ) : null}
              {isSubmitting ? "Đang xác minh…" : "Xác minh email và tiếp tục"}
            </Button>
            <p className="text-center text-xs leading-5 text-[#888482]">
              Nếu cửa sổ đăng nhập hiển thị nhiều tài khoản, hãy chọn đúng địa
              chỉ nhận lời mời.
            </p>
          </>
        )}
      </div>
    </AuthCard>
  );
}
