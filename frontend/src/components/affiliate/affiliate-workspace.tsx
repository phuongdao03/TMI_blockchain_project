"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Copy, UsersRound } from "lucide-react";
import { useState } from "react";

import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import {
  affiliateServiceLabel,
  commissionStatusLabel,
} from "@/lib/affiliate-presentation";
import { affiliateApi } from "@/lib/api/client";
import type { AffiliateCommission, AffiliateReferral } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { formatVnd } from "@/lib/wallet/summary";

const commissionCards = [
  ["onHoldCommissionMinor", "Đang tạm giữ"],
  ["reservedBalanceMinor", "Đang xử lý yêu cầu rút"],
  ["lifetimeEarnedMinor", "Tổng hoa hồng ghi nhận"],
  ["totalWithdrawnMinor", "Đã rút"],
  ["totalReversedMinor", "Đã thu hồi"],
] as const;

function referralLink(value: string, referralCode: string) {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) return "";
    url.pathname = "/";
    url.search = new URLSearchParams({ ref: referralCode }).toString();
    url.hash = "";
    return url.toString();
  } catch {
    return "";
  }
}

function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
      <p className="text-xs font-bold text-[var(--theme-muted)]">{label}</p>
      <p className="mt-2 break-words text-2xl font-bold">{value}</p>
    </div>
  );
}

function ReferralRow({ item }: { item: AffiliateReferral }) {
  return (
    <li className="grid gap-2 border-b border-[var(--theme-border)] py-4 sm:grid-cols-[1fr_auto] sm:items-center">
      <div>
        <p className="font-semibold">Người được giới thiệu</p>
        <p className="text-xs text-[var(--theme-muted)]">
          Ghi nhận {new Date(item.attributedAt).toLocaleDateString("vi-VN")} ·
          hết hạn {new Date(item.expiresAt).toLocaleDateString("vi-VN")}
        </p>
      </div>
      <div className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-3 sm:text-right">
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Giao dịch phát sinh
          </span>
          <strong>{item.conversionCount}</strong>
        </p>
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Doanh thu
          </span>
          <strong>{formatVnd(item.revenueMinor)}</strong>
        </p>
        <p>
          <span className="block text-xs text-[var(--theme-muted)]">
            Hoa hồng
          </span>
          <strong>{formatVnd(item.commissionAmountMinor)}</strong>
        </p>
      </div>
    </li>
  );
}

function CommissionRow({ item }: { item: AffiliateCommission }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div>
        <p className="font-semibold">
          {affiliateServiceLabel(item.serviceCode)}
        </p>
        <p className="text-xs text-[var(--theme-muted)]">
          Cấp {item.commissionLevel} ·{" "}
          {new Date(item.earnedAt).toLocaleDateString("vi-VN")}
        </p>
      </div>
      <div className="text-right">
        <p className="font-bold">{formatVnd(item.commissionAmountMinor)}</p>
        <p className="text-xs text-[var(--theme-muted)]">
          {commissionStatusLabel(item.status)}
        </p>
      </div>
    </li>
  );
}

export function AffiliateWorkspace() {
  const user = useAuthUser();
  const [copied, setCopied] = useState<"code" | "link" | null>(null);
  const [copyError, setCopyError] = useState(false);
  const isEligible =
    Boolean(user?.roles.includes("USER")) &&
    !user?.roles.some((role) => ["MODERATOR", "SUPER_ADMIN"].includes(role));
  const me = useQuery({
    queryKey: ["affiliate", "me", user?.id],
    queryFn: affiliateApi.me,
    enabled: Boolean(user?.id) && isEligible,
    staleTime: 30_000,
  });
  const referrals = useQuery({
    queryKey: ["affiliate", "referrals", user?.id],
    queryFn: affiliateApi.referrals,
    enabled: Boolean(user?.id) && isEligible,
  });
  const commissions = useQuery({
    queryKey: ["affiliate", "commissions", user?.id],
    queryFn: affiliateApi.commissions,
    enabled: Boolean(user?.id) && isEligible,
  });

  if (!isEligible) {
    return (
      <main className="workspace-screen mx-auto max-w-5xl space-y-5 pb-12">
        <WorkspacePageHeader
          description="Theo dõi liên kết giới thiệu và hoa hồng của bạn."
          icon={UsersRound}
          section="Tiếp thị liên kết"
          title="Tiếp thị liên kết"
        />
        <p
          role="status"
          className="rounded-xl border border-[var(--theme-border)] p-4 text-sm"
        >
          Chương trình tiếp thị liên kết dành cho tài khoản người dùng.
        </p>
      </main>
    );
  }

  const data = me.data;
  const safeLink = data
    ? referralLink(data.referralUrl, data.referralCode)
    : "";
  return (
    <main className="workspace-screen mx-auto max-w-5xl space-y-7 pb-12">
      <WorkspacePageHeader
        description="Chia sẻ liên kết giới thiệu để theo dõi lượt đăng ký và hoa hồng."
        icon={UsersRound}
        section="Tiếp thị liên kết"
        title="Tiếp thị liên kết"
      />

      {me.isPending ? (
        <p aria-busy="true" className="py-8 text-center text-sm" role="status">
          Đang tải thông tin giới thiệu…
        </p>
      ) : me.isError || !data ? (
        <div className="rounded-xl border border-red-300 p-4" role="alert">
          <p>Chưa tải được thông tin giới thiệu. Vui lòng thử lại.</p>
          <button
            className="mt-2 min-h-11 font-bold underline"
            onClick={() => void me.refetch()}
            type="button"
          >
            Thử tải lại
          </button>
        </div>
      ) : (
        <>
          <section
            aria-label="Mã giới thiệu của bạn"
            className="space-y-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
          >
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--theme-muted)]">
                Mã giới thiệu của bạn
              </p>
              <p className="mt-1 break-all font-mono text-2xl font-bold tracking-wide">
                {data.referralCode}
              </p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
                Chia sẻ mã hoặc liên kết này. Khi người được mời đăng ký và phát
                sinh giao dịch đủ điều kiện, hoa hồng sẽ được ghi nhận theo
                chính sách hiện hành.
              </p>
            </div>
            <label className="grid gap-1 text-sm font-semibold">
              Liên kết giới thiệu
              <input
                className="min-h-11 w-full min-w-0 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 font-mono text-sm"
                readOnly
                value={safeLink || "Liên kết chưa khả dụng"}
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold"
                onClick={() => {
                  if (!navigator.clipboard?.writeText) {
                    setCopied(null);
                    setCopyError(true);
                    return;
                  }
                  setCopyError(false);
                  void navigator.clipboard
                    .writeText(data.referralCode)
                    .then(() => setCopied("code"))
                    .catch(() => {
                      setCopied(null);
                      setCopyError(true);
                    });
                }}
                type="button"
              >
                {copied === "code" ? (
                  <Check aria-hidden="true" className="size-4" />
                ) : (
                  <Copy aria-hidden="true" className="size-4" />
                )}
                {copied === "code" ? "Đã sao chép mã" : "Sao chép mã"}
              </button>
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold disabled:opacity-50"
                disabled={!safeLink}
                onClick={() => {
                  if (!safeLink || !navigator.clipboard?.writeText) {
                    setCopied(null);
                    setCopyError(true);
                    return;
                  }
                  setCopyError(false);
                  void navigator.clipboard
                    .writeText(safeLink)
                    .then(() => setCopied("link"))
                    .catch(() => {
                      setCopied(null);
                      setCopyError(true);
                    });
                }}
                type="button"
              >
                {copied === "link" ? (
                  <Check aria-hidden="true" className="size-4" />
                ) : (
                  <Copy aria-hidden="true" className="size-4" />
                )}
                {copied === "link"
                  ? "Đã sao chép liên kết"
                  : "Sao chép liên kết"}
              </button>
              <button
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold disabled:opacity-50"
                disabled={!safeLink}
                onClick={() => {
                  if (!safeLink) return;
                  if (!navigator.share) {
                    setCopyError(true);
                    return;
                  }
                  setCopyError(false);
                  void navigator
                    .share({
                      title: "Mời bạn tham gia Tinh Hoa Việt",
                      text: "Đăng ký qua liên kết giới thiệu của tôi.",
                      url: safeLink,
                    })
                    .catch((error: unknown) => {
                      if (
                        error instanceof DOMException &&
                        error.name === "AbortError"
                      ) {
                        return;
                      }
                      setCopyError(true);
                    });
                }}
                type="button"
              >
                Chia sẻ
              </button>
            </div>
            {copyError ? (
              <p role="alert" className="text-sm text-red-700">
                Không thực hiện được thao tác. Hãy chọn và sao chép nội dung
                trong ô liên kết.
              </p>
            ) : null}
          </section>

          <section
            aria-label="Tổng quan giới thiệu và hoa hồng"
            className="grid gap-3 sm:grid-cols-3"
          >
            <MetricCard
              label="Người đăng ký qua bạn"
              value={data.attributedUserCount}
            />
            <MetricCard
              label="Hoa hồng có thể rút"
              value={formatVnd(data.availableBalanceMinor)}
            />
            <MetricCard
              label="Hoa hồng chờ xác nhận"
              value={formatVnd(data.pendingCommissionMinor)}
            />
          </section>

          <details className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4">
            <summary className="min-h-10 cursor-pointer py-2 text-sm font-bold">
              Xem thêm số liệu giới thiệu và hoa hồng
            </summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <MetricCard label="Lượt truy cập" value={data.clickCount} />
              {commissionCards.map(([key, label]) => (
                <MetricCard
                  key={key}
                  label={label}
                  value={formatVnd(data[key])}
                />
              ))}
            </div>
          </details>

          <section aria-labelledby="commission-summary-title">
            <h2 id="commission-summary-title" className="text-xl font-bold">
              Cách tính hoa hồng
            </h2>
            <p className="mt-3 text-sm text-[var(--theme-muted)]">
              Hoa hồng được tính từ giao dịch đủ điều kiện theo chính sách hiện
              hành, tối đa hai cấp. Khoản tiền cần được duyệt và qua thời gian
              tạm giữ trước khi có thể yêu cầu rút; yêu cầu rút do quản trị viên
              xử lý.
            </p>
          </section>
        </>
      )}

      <section
        aria-labelledby="referral-history-title"
        className="space-y-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
      >
        <h2
          id="referral-history-title"
          className="text-lg font-bold sm:text-xl"
        >
          Lượt giới thiệu gần đây
        </h2>
        {referrals.isPending ? (
          <p aria-busy="true" className="py-5 text-sm" role="status">
            Đang tải lượt giới thiệu…
          </p>
        ) : referrals.isError ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
            role="alert"
          >
            <p className="text-sm text-red-700">
              Chưa tải được lịch sử giới thiệu.
            </p>
            <button
              className="min-h-10 font-bold underline"
              onClick={() => void referrals.refetch()}
              type="button"
            >
              Tải lại
            </button>
          </div>
        ) : referrals.data?.length ? (
          <ul className="mt-2 divide-y divide-[var(--theme-border)]">
            {referrals.data.map((item) => (
              <ReferralRow item={item} key={item.id} />
            ))}
          </ul>
        ) : (
          <p className="mt-3 rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
            Chưa ghi nhận lượt giới thiệu nào.
          </p>
        )}
      </section>

      <section
        aria-labelledby="commission-history-title"
        className="space-y-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5"
      >
        <h2
          id="commission-history-title"
          className="text-lg font-bold sm:text-xl"
        >
          Lịch sử hoa hồng
        </h2>
        {commissions.isPending ? (
          <p aria-busy="true" className="py-5 text-sm" role="status">
            Đang tải lịch sử hoa hồng…
          </p>
        ) : commissions.isError ? (
          <div
            className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
            role="alert"
          >
            <p className="text-sm text-red-700">
              Chưa tải được lịch sử hoa hồng.
            </p>
            <button
              className="min-h-10 font-bold underline"
              onClick={() => void commissions.refetch()}
              type="button"
            >
              Tải lại
            </button>
          </div>
        ) : commissions.data?.length ? (
          <ul className="mt-2 divide-y divide-[var(--theme-border)]">
            {commissions.data.map((item) => (
              <CommissionRow item={item} key={item.id} />
            ))}
          </ul>
        ) : (
          <p className="mt-3 rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">
            Bạn chưa có khoản hoa hồng nào.
          </p>
        )}
      </section>
    </main>
  );
}
