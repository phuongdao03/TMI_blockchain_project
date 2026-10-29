import Image from "next/image";
import Link from "next/link";
import { Ticket } from "lucide-react";
import type { SavedVoucher } from "@/lib/api/voucher-types";
import { formatVnd } from "@/lib/wallet/summary";

export function voucherDestination(voucher: SavedVoucher) {
  const services = voucher.policy?.serviceCodes ?? ["DOSSIER_SUBMISSION"];
  if (
    services.includes("DOSSIER_SUBMISSION") ||
    services.includes("DOSSIER_APPROVAL")
  )
    return "/dossiers";
  if (services.includes("MEMBERSHIP")) return "/membership";
  if (services.includes("ADVERTISING")) return "/advertising";
  return "/workspace";
}
export function VoucherCard({
  voucher,
  detail = false,
}: {
  voucher: SavedVoucher;
  detail?: boolean;
}) {
  const policy = voucher.policy;
  const image = policy?.presentation.cardImageAssetId
    ? `/api/v1/promotion-media/${policy.presentation.cardImageAssetId}`
    : voucher.imagePath;
  const available =
    !voucher.expired && (!voucher.status || voucher.status === "AVAILABLE");
  const state = voucher.expired
    ? "Đã hết hạn"
    : voucher.status === "REDEEMED"
      ? "Đã sử dụng"
      : voucher.status === "RESERVED"
        ? "Đang giữ cho thanh toán"
        : voucher.status === "REVOKED"
          ? "Đã thu hồi"
          : "Đã nhận";
  return (
    <article className="h-full overflow-hidden rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
      {image && (
        <Image
          src={image}
          alt={policy?.presentation.altText ?? voucher.title}
          width={640}
          height={400}
          unoptimized={image.startsWith("/api/")}
          className={`w-full object-contain ${detail ? "max-h-96" : "h-40"}`}
        />
      )}
      <div className="space-y-3 p-5 sm:p-6">
        <p className="flex items-center gap-2 text-sm font-semibold text-[var(--theme-muted)]">
          <Ticket aria-hidden="true" className="size-5" />
          {state}
        </p>
        <h2 className="text-lg font-semibold text-[var(--theme-text)]">
          {voucher.title}
        </h2>
        <p className="text-3xl font-bold text-[var(--theme-text)]">
          {policy?.discountType === "PERCENT"
            ? `${policy.percentageBps / 100}%`
            : formatVnd(voucher.amountVnd)}
        </p>
        {policy?.discountType === "PERCENT" && policy.discountCapVnd && (
          <p className="text-sm text-[var(--theme-muted)]">
            Giảm tối đa {formatVnd(policy.discountCapVnd)}
          </p>
        )}
        <p className="text-sm leading-6 text-[var(--theme-muted)]">
          {voucher.terms}
        </p>
        {policy && (
          <p className="text-xs text-[var(--theme-muted)]">
            Dịch vụ:{" "}
            {policy.serviceCodes
              .map(
                (service) =>
                  ({
                    DOSSIER_SUBMISSION: "Phí nộp hồ sơ",
                    DOSSIER_APPROVAL: "Phí sau phê duyệt",
                    MEMBERSHIP: "Hội viên",
                    ADVERTISING: "Quảng cáo",
                  })[service] ?? service,
              )
              .join(", ")}
            {policy.minimumOrderVnd > 0
              ? ` · Đơn từ ${formatVnd(policy.minimumOrderVnd)}`
              : ""}
          </p>
        )}
        {voucher.uniqueCode && (
          <p className="break-all text-sm text-[var(--theme-text)]">
            Mã: <strong>{voucher.uniqueCode}</strong>
          </p>
        )}
        <p className="text-sm text-[var(--theme-muted)]">
          Hạn dùng:{" "}
          <time dateTime={voucher.expiresAt}>
            {new Intl.DateTimeFormat("vi-VN", {
              dateStyle: "long",
              timeStyle: "short",
              timeZone: "Asia/Ho_Chi_Minh",
            }).format(new Date(voucher.expiresAt))}
          </time>
        </p>
        {voucher.redeemedAt && (
          <p className="text-sm text-[var(--theme-muted)]">
            Đã sử dụng: {new Date(voucher.redeemedAt).toLocaleString("vi-VN")}
          </p>
        )}
        <div className="flex flex-wrap gap-3 pt-2">
          {available && (
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-semibold text-[var(--theme-accent-contrast,#fff)]"
              href={voucherDestination(voucher)}
            >
              Dùng ưu đãi
            </Link>
          )}
          {!detail && (
            <Link
              className="inline-flex min-h-11 items-center px-3 text-sm font-semibold text-[var(--theme-text)]"
              href={`/vouchers/${voucher.id}`}
            >
              Xem chi tiết
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}
