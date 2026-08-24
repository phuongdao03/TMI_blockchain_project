"use client";

import {
  GoogleAuthProvider,
  TotpMultiFactorGenerator,
  multiFactor,
  signInWithPopup,
  signOut,
  type TotpSecret,
} from "firebase/auth";
import { ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthCard, AuthLink } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { ApiError, authApi } from "@/lib/api/client";
import { firebaseConfigured, getFirebaseAuth } from "@/lib/firebase/client";

export function StaffMfaRecoveryForm() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();
  const [secret, setSecret] = useState<TotpSecret>();
  const [code, setCode] = useState("");

  async function authorize() {
    setPending(true);
    setError(undefined);
    try {
      if (!firebaseConfigured()) throw new Error("Firebase is not configured");
      const credential = await signInWithPopup(
        getFirebaseAuth(),
        new GoogleAuthProvider(),
      );
      await authApi.authorizeStaffMfaRecovery(
        await credential.user.getIdToken(true),
      );
      const session = await multiFactor(credential.user).getSession();
      setSecret(await TotpMultiFactorGenerator.generateSecret(session));
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể bắt đầu khôi phục. Hãy liên hệ người quản trị phụ trách.",
      );
    } finally {
      setPending(false);
    }
  }

  async function enroll() {
    const user = getFirebaseAuth().currentUser;
    if (!user || !secret || !/^\d{6}$/.test(code)) return;
    setPending(true);
    setError(undefined);
    try {
      await multiFactor(user).enroll(
        TotpMultiFactorGenerator.assertionForEnrollment(secret, code),
        "TMI Authenticator",
      );
      await signOut(getFirebaseAuth());
      router.replace("/login?mfa=recovered");
      router.refresh();
    } catch {
      setError("Mã xác minh không đúng hoặc đã hết hạn. Vui lòng thử lại.");
      setPending(false);
    }
  }

  return (
    <AuthCard
      description="Chỉ sử dụng trang này sau khi người quản trị đã xác nhận yêu cầu khôi phục của bạn."
      footer={<AuthLink href="/login">Quay lại đăng nhập</AuthLink>}
      title="Khôi phục bảo vệ tài khoản"
    >
      <div className="space-y-4">
        <p className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-4 text-sm leading-6 text-[#aaa6a4]">
          <ShieldCheck
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-[#F6C515]"
          />
          Yêu cầu khôi phục có hiệu lực 24 giờ. Mọi phiên đăng nhập cũ đã bị
          khóa và nhiệm vụ của bạn không thay đổi.
        </p>
        {error ? (
          <p
            className="rounded-lg border border-red-400/40 bg-red-950/30 p-3 text-sm text-red-200"
            role="alert"
          >
            {error}
          </p>
        ) : null}
        {secret ? (
          <div className="space-y-4">
            <p className="text-sm leading-6 text-[#aaa6a4]">
              Nhập khóa sau vào ứng dụng xác thực mới, sau đó điền mã 6 số.
            </p>
            <code className="block break-all rounded-md bg-black/40 p-3 text-sm text-white">
              {secret.secretKey}
            </code>
            <label
              className="block text-sm font-semibold"
              htmlFor="recovery-totp-code"
            >
              Mã xác minh 6 số
            </label>
            <input
              autoComplete="one-time-code"
              className="min-h-12 w-full rounded-md border border-white/20 bg-[#111] px-3 text-center font-mono text-lg tracking-[0.3em] text-white outline-none focus:border-[#F6C515]"
              id="recovery-totp-code"
              inputMode="numeric"
              maxLength={6}
              onChange={(event) =>
                setCode(event.target.value.replace(/\D/g, ""))
              }
              value={code}
            />
            <Button
              className="w-full"
              disabled={pending || code.length !== 6}
              onClick={enroll}
              type="button"
            >
              {pending ? "Đang kích hoạt…" : "Kích hoạt ứng dụng mới"}
            </Button>
          </div>
        ) : (
          <Button
            className="w-full"
            disabled={pending}
            onClick={authorize}
            type="button"
          >
            {pending ? "Đang xác minh…" : "Xác minh danh tính"}
          </Button>
        )}
      </div>
    </AuthCard>
  );
}
