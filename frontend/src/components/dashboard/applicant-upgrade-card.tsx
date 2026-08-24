"use client";

import {
  ArrowRight,
  Building2,
  FileUp,
  LoaderCircle,
  UserRound,
} from "lucide-react";
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
  const [isChoosing, setIsChoosing] = useState(false);

  const upgrade = async () => {
    setError(undefined);
    setIsSubmitting(true);
    try {
      const user = await authApi.upgradeToApplicant(accountType);
      setCompleted(true);
      onUpgraded?.(user);
    } catch (reason) {
      setError(
        reason instanceof ApiError && reason.status === 401
          ? "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục."
          : "Chưa thể bắt đầu hồ sơ lúc này. Vui lòng thử lại sau.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-black/10 bg-[#fbfaf7] shadow-[0_18px_55px_rgb(29_28_27/0.08)]">
      <div className="grid gap-7 p-6 sm:p-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div className="max-w-2xl">
          <span className="grid size-11 place-items-center rounded-lg bg-primary-50 text-primary-700">
            <FileUp aria-hidden="true" className="size-5" />
          </span>
          <p className="mt-6 font-mono text-[0.65rem] font-bold uppercase tracking-[0.18em] text-primary-700">
            Bắt đầu khi bạn sẵn sàng
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-[-0.03em] text-neutral-950 sm:text-3xl">
            Gửi tác phẩm hoặc hồ sơ
          </h2>
          <p className="mt-3 text-sm leading-6 text-neutral-600">
            Chuẩn bị thông tin, tải tài liệu lên và theo dõi tiến độ tại một
            nơi.
          </p>
        </div>
        {!isChoosing && !completed ? (
          <Button
            className="min-h-12"
            onClick={() => setIsChoosing(true)}
            type="button"
          >
            Gửi tác phẩm hoặc hồ sơ
            <ArrowRight aria-hidden="true" className="size-4" />
          </Button>
        ) : null}
      </div>

      {completed ? (
        <div
          className="border-t border-emerald-200 bg-emerald-50 px-6 py-5 text-sm text-emerald-800 sm:px-8"
          role="status"
        >
          <p className="font-bold">Bạn đã có thể bắt đầu hồ sơ.</p>
          <p className="mt-1">
            Hoàn thiện thông tin liên hệ trước khi tải tài liệu lên.
          </p>
          <a className="mt-3 inline-block font-bold underline" href="/account">
            Tiếp tục thiết lập
          </a>
        </div>
      ) : isChoosing ? (
        <>
          <fieldset className="grid gap-3 border-t border-black/10 bg-white px-6 py-6 sm:grid-cols-2 sm:px-8">
            <legend className="mb-4 text-base font-bold text-neutral-950 sm:col-span-2">
              Bạn gửi hồ sơ với tư cách nào?
            </legend>
            <label className="cursor-pointer rounded-xl border border-neutral-200 p-4 transition has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50">
              <input
                aria-label="Cá nhân"
                checked={accountType === "INDIVIDUAL_APPLICANT"}
                className="sr-only"
                name="applicant-account-type"
                onChange={() => setAccountType("INDIVIDUAL_APPLICANT")}
                type="radio"
              />
              <span className="flex items-center gap-2 font-bold text-neutral-950">
                <UserRound
                  aria-hidden="true"
                  className="size-4 text-primary-700"
                />
                Cá nhân
              </span>
              <span className="mt-2 block text-sm text-neutral-500">
                Hồ sơ do bạn trực tiếp gửi.
              </span>
            </label>
            <label className="cursor-pointer rounded-xl border border-neutral-200 p-4 transition has-[:checked]:border-primary-600 has-[:checked]:bg-primary-50">
              <input
                aria-label="Doanh nghiệp hoặc tổ chức"
                checked={accountType === "ORGANIZATION_APPLICANT"}
                className="sr-only"
                name="applicant-account-type"
                onChange={() => setAccountType("ORGANIZATION_APPLICANT")}
                type="radio"
              />
              <span className="flex items-center gap-2 font-bold text-neutral-950">
                <Building2
                  aria-hidden="true"
                  className="size-4 text-primary-700"
                />
                Doanh nghiệp hoặc tổ chức
              </span>
              <span className="mt-2 block text-sm text-neutral-500">
                Hồ sơ được gửi thay mặt một đơn vị.
              </span>
            </label>
          </fieldset>
          {error ? (
            <p
              className="px-6 pt-4 text-sm font-semibold text-error sm:px-8"
              role="alert"
            >
              {error}
            </p>
          ) : null}
          <div className="flex flex-col-reverse gap-3 border-t border-black/8 px-6 py-5 sm:flex-row sm:items-center sm:justify-end sm:px-8">
            <button
              className="min-h-11 px-4 text-sm font-bold text-neutral-600 hover:text-neutral-950"
              onClick={() => setIsChoosing(false)}
              type="button"
            >
              Để sau
            </button>
            <Button
              className="min-h-11"
              disabled={isSubmitting}
              onClick={upgrade}
              type="button"
            >
              {isSubmitting ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="size-4 animate-spin"
                />
              ) : null}
              {isSubmitting ? "Đang thiết lập…" : "Tiếp tục"}
            </Button>
          </div>
        </>
      ) : null}
    </section>
  );
}
