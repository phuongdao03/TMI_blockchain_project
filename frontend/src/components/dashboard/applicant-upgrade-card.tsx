"use client";

import { LoaderCircle, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { authApi, ApiError } from "@/lib/api/client";
import type { AuthUser } from "@/lib/api/types";
import { Button } from "@/components/ui/button";

type ApplicantAccountType = "INDIVIDUAL_APPLICANT" | "ORGANIZATION_APPLICANT";

export function ApplicantUpgradeCard({
  onUpgraded,
}: {
  onUpgraded?: (user: AuthUser) => void;
}) {
  const [accountType, setAccountType] = useState<ApplicantAccountType>(
    "INDIVIDUAL_APPLICANT",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();
  const [completed, setCompleted] = useState(false);

  const upgrade = async () => {
    setError(undefined);
    setIsSubmitting(true);
    try {
      const user = await authApi.upgradeToApplicant(accountType);
      setCompleted(true);
      onUpgraded?.(user);
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : "Không thể mở luồng gửi tài sản lúc này.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="rounded-3xl border border-primary-200 bg-white p-6 shadow-sm sm:p-7">
      <div className="flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary-50 text-primary-700">
          <ShieldCheck aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-primary-700">
            Gửi tài sản lên TMI
          </p>
          <h2 className="mt-1 text-xl font-black text-neutral-950">
            Không cần tạo tài khoản mới
          </h2>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            Nâng cấp tài khoản hiện tại khi bạn đã sẵn sàng. Bạn vẫn có thể xem
            và bình chọn như bình thường.
          </p>
        </div>
      </div>

      {completed ? (
        <div className="mt-6 rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-800" role="status">
          <p className="font-bold">Đã mở không gian gửi tài sản.</p>
          <p className="mt-1">Hoàn thiện họ tên trong hồ sơ tài khoản trước khi tạo hồ sơ xác lập.</p>
          <a className="mt-3 inline-block font-bold underline" href="/tai-khoan">
            Mở cài đặt tài khoản
          </a>
        </div>
      ) : (
        <>
          <fieldset className="mt-6 grid gap-3 sm:grid-cols-2">
            <legend className="sr-only">Loại hồ sơ người gửi</legend>
            <label className="rounded-2xl border border-neutral-200 p-4 has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50">
              <input
                aria-label="Cá nhân"
                checked={accountType === "INDIVIDUAL_APPLICANT"}
                className="sr-only"
                name="applicant-account-type"
                onChange={() => setAccountType("INDIVIDUAL_APPLICANT")}
                type="radio"
              />
              <span className="font-bold text-neutral-950">Cá nhân</span>
              <span className="mt-1 block text-sm text-neutral-500">
                Gửi tài sản thuộc quyền sở hữu cá nhân.
              </span>
            </label>
            <label className="rounded-2xl border border-neutral-200 p-4 has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50">
              <input
                aria-label="Tổ chức"
                checked={accountType === "ORGANIZATION_APPLICANT"}
                className="sr-only"
                name="applicant-account-type"
                onChange={() => setAccountType("ORGANIZATION_APPLICANT")}
                type="radio"
              />
              <span className="font-bold text-neutral-950">Tổ chức</span>
              <span className="mt-1 block text-sm text-neutral-500">
                Đại diện đơn vị và quản lý thành viên.
              </span>
            </label>
          </fieldset>
          {error ? (
            <p className="mt-4 text-sm font-semibold text-error" role="alert">
              {error}
            </p>
          ) : null}
          <Button
            className="mt-6 min-h-11"
            disabled={isSubmitting}
            onClick={upgrade}
            type="button"
          >
            {isSubmitting ? (
              <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
            ) : null}
            Bắt đầu gửi tài sản
          </Button>
        </>
      )}
    </section>
  );
}
