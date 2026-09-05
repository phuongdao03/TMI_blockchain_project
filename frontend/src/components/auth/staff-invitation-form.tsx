"use client";

import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
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
  const validToken = typeof token === "string" && token.length >= 32;

  async function acceptInvitation() {
    if (!validToken) return;
    setIsSubmitting(true);
    setError(undefined);
    try {
      if (!firebaseConfigured()) throw new Error("Firebase is not configured");
      const credential = await signInWithPopup(
        getFirebaseAuth(),
        new GoogleAuthProvider(),
      );
      const idToken = await credential.user.getIdToken(true);
      await authApi.acceptStaffInvitation(token, idToken);
      router.replace("/login?invitation=accepted");
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Không thể xác nhận lời mời. Hãy dùng đúng email đã nhận thư và thử lại.",
      );
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
            Liên kết lời mời không hợp lệ. Hãy yêu cầu người quản trị gửi lời
            mời mới.
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
        <Button
          className="w-full"
          disabled={!validToken || isSubmitting}
          onClick={acceptInvitation}
          type="button"
        >
          {isSubmitting ? (
            <LoaderCircle aria-hidden="true" className="size-5 animate-spin" />
          ) : null}
          {isSubmitting
            ? "Đang xác minh…"
            : "Xác minh email và kích hoạt tài khoản"}
        </Button>
      </div>
    </AuthCard>
  );
}
