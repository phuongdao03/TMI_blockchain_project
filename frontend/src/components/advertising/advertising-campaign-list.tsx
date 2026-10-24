import {
  ArrowRight,
  CalendarDays,
  ChartNoAxesCombined,
  Megaphone,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import type {
  AdvertisingCampaignStatus,
  AdvertisingCampaignSummary,
} from "@/lib/api/types";

type AdvertisingCampaignListProps = {
  campaigns: AdvertisingCampaignSummary[];
  onCreateCampaign: () => void;
  onScheduleCampaign: (campaignId: string) => void;
  onShowMetrics?: (campaignId: string) => void;
  onEditCreative?: (campaignId: string) => void;
};

const campaignStatusLabels: Record<AdvertisingCampaignStatus, string> = {
  DRAFT: "Bản nháp",
  PENDING_REVIEW: "Đang chờ duyệt nội dung",
  APPROVED: "Đã duyệt nội dung",
  PENDING_PAYMENT: "Chờ thanh toán",
  SCHEDULED: "Đã xếp lịch",
  NEEDS_RESCHEDULE: "Cần chọn lại lịch",
  ACTIVE: "Đang phân phối",
  PAUSED: "Đang tạm dừng",
  COMPLETED: "Đã kết thúc",
  CANCELLED: "Đã hủy",
  REJECTED: "Cần cập nhật nội dung",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusTone(status: AdvertisingCampaignStatus): string {
  if (status === "ACTIVE" || status === "APPROVED") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "PENDING_REVIEW" || status === "PENDING_PAYMENT") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  if (status === "REJECTED" || status === "NEEDS_RESCHEDULE") {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  return "border-[var(--theme-border)] bg-[var(--theme-elevated)] text-[var(--theme-muted)]";
}

export function AdvertisingCampaignList({
  campaigns,
  onCreateCampaign,
  onScheduleCampaign,
  onShowMetrics,
  onEditCreative,
}: AdvertisingCampaignListProps) {
  if (campaigns.length === 0) {
    return (
      <section className="rounded-2xl border border-dashed border-[var(--theme-border)] bg-[var(--theme-surface)] px-5 py-12 text-center sm:px-8">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-primary-50 text-primary-800">
          <Megaphone aria-hidden="true" className="size-7" />
        </span>
        <h2 className="mt-5 text-xl font-bold text-[var(--theme-text)]">
          Chưa có chiến dịch quảng cáo
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-[var(--theme-muted)]">
          Chọn một hồ sơ đủ điều kiện, nội dung quảng cáo và thời lượng phù hợp
          để bắt đầu.
        </p>
        <Button className="mt-6" onClick={onCreateCampaign}>
          Tạo chiến dịch <ArrowRight aria-hidden="true" className="size-4" />
        </Button>
      </section>
    );
  }

  return (
    <section aria-labelledby="advertising-campaigns-heading">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--theme-accent)]">
            Theo dõi và tối ưu
          </p>
          <h2
            className="mt-1 text-xl font-bold text-[var(--theme-text)]"
            id="advertising-campaigns-heading"
          >
            Chiến dịch của bạn
          </h2>
        </div>
        <Button onClick={onCreateCampaign} variant="outline">
          <Megaphone aria-hidden="true" className="size-4" /> Tạo chiến dịch
        </Button>
      </div>

      <ul className="grid gap-4 xl:grid-cols-2">
        {campaigns.map((campaign) => {
          const canSchedule =
            campaign.status === "APPROVED" ||
            campaign.status === "NEEDS_RESCHEDULE" ||
            campaign.status === "PENDING_PAYMENT";
          const hasBooking = Boolean(
            campaign.bookingStartAt || campaign.paymentStatus === "PAID",
          );
          const scheduleLabel =
            campaign.status === "NEEDS_RESCHEDULE"
              ? "Chọn lịch thay thế"
              : campaign.status === "PENDING_PAYMENT"
                ? "Hoàn tất thanh toán"
                : "Chọn lịch quảng cáo";
          const scheduledAt =
            campaign.bookingStartAt ??
            campaign.actualStartAt ??
            campaign.desiredStartAt;

          return (
            <li key={campaign.id}>
              <article className="h-full rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="font-mono text-[0.68rem] font-semibold tracking-[0.12em] text-[var(--theme-muted)]">
                    {campaign.placementCode.replaceAll("_", " ")}
                  </p>
                  <span
                    className={`inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-semibold ${statusTone(campaign.status)}`}
                  >
                    {campaignStatusLabels[campaign.status]}
                  </span>
                </div>
                <h3 className="mt-4 text-lg font-bold leading-snug text-[var(--theme-text)]">
                  {campaign.creativeTitle ?? "Chiến dịch chưa có tiêu đề"}
                </h3>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">
                  Hồ sơ gắn với quảng cáo · {campaign.placementName}
                </p>

                <dl className="mt-5 grid grid-cols-2 gap-3 border-y border-[var(--theme-border)] py-4 text-sm">
                  <div>
                    <dt className="text-xs text-[var(--theme-muted)]">
                      Lịch chạy
                    </dt>
                    <dd className="mt-1 flex items-start gap-2 font-semibold text-[var(--theme-text)]">
                      <CalendarDays
                        aria-hidden="true"
                        className="mt-0.5 size-4 shrink-0 text-[var(--theme-accent)]"
                      />
                      {scheduledAt ? formatDate(scheduledAt) : "Chưa chọn"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-[var(--theme-muted)]">
                      Lượt phân phối
                    </dt>
                    <dd className="mt-1 flex items-start gap-2 font-semibold text-[var(--theme-text)]">
                      <ChartNoAxesCombined
                        aria-hidden="true"
                        className="mt-0.5 size-4 shrink-0 text-[var(--theme-accent)]"
                      />
                      {new Intl.NumberFormat("vi-VN").format(
                        campaign.deliveryCount,
                      )}
                    </dd>
                  </div>
                </dl>

                {campaign.creativeReviewNote ? (
                  <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-950">
                    Ghi chú duyệt: {campaign.creativeReviewNote}
                  </p>
                ) : null}
                {campaign.paymentStatus === "PAID" ? (
                  <p className="mt-3 text-xs font-medium text-emerald-800">
                    Đã thanh toán bằng ví nội bộ
                  </p>
                ) : hasBooking ? (
                  <p className="mt-3 text-xs font-medium text-amber-800">
                    Lịch đang giữ chỗ. Hoàn tất thanh toán để xác nhận.
                  </p>
                ) : null}

                <div className="mt-4 flex flex-wrap gap-2">
                  {canSchedule &&
                  (!hasBooking || campaign.status === "PENDING_PAYMENT") ? (
                    <Button
                      onClick={() => onScheduleCampaign(campaign.id)}
                      variant="outline"
                    >
                      <CalendarDays aria-hidden="true" className="size-4" />
                      {scheduleLabel}
                    </Button>
                  ) : null}
                  {campaign.paymentStatus === "PAID" && onShowMetrics ? (
                    <Button
                      onClick={() => onShowMetrics(campaign.id)}
                      variant="outline"
                    >
                      Xem hiệu quả{" "}
                      <ArrowRight aria-hidden="true" className="size-4" />
                    </Button>
                  ) : null}
                  {campaign.status === "REJECTED" && onEditCreative ? (
                    <Button
                      onClick={() => onEditCreative(campaign.id)}
                      variant="outline"
                    >
                      Sửa nội dung và gửi lại{" "}
                      <ArrowRight aria-hidden="true" className="size-4" />
                    </Button>
                  ) : null}
                </div>
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
