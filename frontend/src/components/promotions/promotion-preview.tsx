"use client";

import Image from "next/image";
import type { CampaignInput } from "@/lib/api/promotion-types";
import { formatVnd } from "@/lib/wallet/summary";

export function PromotionPreview({
  campaign,
  mobile = false,
}: {
  campaign: CampaignInput;
  mobile?: boolean;
}) {
  const display = campaign.policy.presentation;
  const compact = display.template === "MINIMAL";
  const [red = 0, green = 0, blue = 0] = [1, 3, 5].map((start) =>
    parseInt(display.ctaColor.slice(start, start + 2), 16),
  );
  const ctaText =
    (red * 299 + green * 587 + blue * 114) / 1000 > 145 ? "#241515" : "#ffffff";
  const assetId =
    mobile && display.mobileImageAssetId
      ? display.mobileImageAssetId
      : display.imageAssetId;
  const image = assetId
    ? `/api/v1/promotion-media/${assetId}`
    : campaign.imagePath;
  return (
    <article
      aria-label="Xem trước thông báo voucher"
      className="mx-auto w-full overflow-hidden border border-black/10 shadow-sm"
      style={{
        maxWidth: mobile ? 375 : 760,
        backgroundColor: display.backgroundColor,
        color: display.textColor,
        borderRadius: display.borderRadius,
      }}
    >
      <div className={mobile || compact ? "grid" : "grid sm:grid-cols-2"}>
        {!compact && image && (
          <div className="flex items-center justify-center bg-black/5">
            <Image
              src={image}
              alt={display.altText || "Voucher Tinh Hoa Việt"}
              width={640}
              height={800}
              unoptimized={image.startsWith("/api/")}
              className="max-h-72 w-full"
              style={{
                objectFit: display.imageFit,
                objectPosition: `${display.focalX}% ${display.focalY}%`,
              }}
            />
          </div>
        )}
        <div className="space-y-4 p-6">
          <p className="text-xs font-bold uppercase tracking-widest">
            {display.subtitle || "Ưu đãi dành cho bạn"}
          </p>
          <h3 className="text-2xl font-bold leading-tight">
            {campaign.title || "Tiêu đề ưu đãi"}
          </h3>
          {display.template === "PREMIUM" && (
            <p className="text-3xl font-bold">
              {campaign.policy.discountType === "PERCENT"
                ? `${campaign.policy.percentageBps / 100}%`
                : formatVnd(campaign.amountVnd)}
            </p>
          )}
          <p className="text-sm leading-6">
            {campaign.description ||
              "Nội dung của chương trình sẽ hiển thị tại đây."}
          </p>
          <p className="text-xs leading-6 opacity-80">{campaign.terms}</p>
          <p className="text-xs">
            {campaign.policy.fixedExpiresAt
              ? `Đến ${new Date(campaign.policy.fixedExpiresAt).toLocaleDateString("vi-VN")}`
              : `${campaign.validityDays} ngày kể từ khi cấp`}
          </p>
          <span
            className="block rounded-lg px-4 py-3 text-center text-sm font-semibold text-white"
            style={{ backgroundColor: display.ctaColor, color: ctaText }}
          >
            {display.primaryCta}
          </span>
          <p className="text-center text-xs">{display.secondaryCta}</p>
        </div>
      </div>
    </article>
  );
}
