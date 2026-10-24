"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  CalendarDays,
  CircleAlert,
  Clock3,
  LoaderCircle,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState, type ChangeEvent } from "react";

import { formatVnd, walletKey } from "@/components/wallet/wallet-workspace";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { advertisingApi, ApiError, walletApi } from "@/lib/api/client";
import type {
  AdvertisingAvailability,
  AdvertisingCampaignSummary,
  AdvertisingPackage,
  AdvertisingReservationCheckout,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const fieldClassName =
  "min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)] outline-none focus-visible:ring-2 focus-visible:ring-primary-500";

function defaultStartValue(): string {
  const start = new Date();
  start.setDate(start.getDate() + 1);
  start.setHours(10, 0, 0, 0);
  const local = new Date(start.getTime() - start.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function localInputValue(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function isoValue(value: string): string | null {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Yêu cầu chưa hoàn tất. Vui lòng thử lại.";
}

function relativeDateLabel(value: string): string {
  return `${new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value))}`;
}

function AvailabilityCard({
  availability,
  isPending,
  error,
  onSelectAlternative,
  onWaitlist,
  waiting,
  replacement,
  selectedAt,
}: {
  availability?: AdvertisingAvailability;
  isPending: boolean;
  error: unknown;
  onSelectAlternative: (value: string) => void;
  onWaitlist: () => void;
  waiting: boolean;
  replacement: boolean;
  selectedAt: string | null;
}) {
  if (isPending) {
    return (
      <p
        className="flex items-center gap-2 rounded-xl bg-[var(--theme-elevated)] p-3 text-sm text-[var(--theme-muted)]"
        role="status"
      >
        <LoaderCircle
          aria-hidden="true"
          className="thv-loading-spinner size-4"
        />
        Đang kiểm tra sức chứa cho toàn bộ thời lượng…
      </p>
    );
  }
  if (error) {
    return (
      <p
        className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
        role="alert"
      >
        Không thể kiểm tra lịch. Vui lòng đổi ngày hoặc thử lại.
      </p>
    );
  }
  if (!availability || !selectedAt) return null;
  if (availability.available) {
    return (
      <p
        className="flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm leading-6 text-emerald-950"
        role="status"
      >
        <CalendarDays aria-hidden="true" className="mt-1 size-4 shrink-0" />
        Còn {availability.remainingSlots} suất từ{" "}
        {formatDateTime(availability.startAt)} đến{" "}
        {formatDateTime(availability.endAt)}.
      </p>
    );
  }
  return (
    <div
      className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950"
      role="status"
    >
      <p className="font-semibold">
        Ngày này đã kín chỗ trong toàn bộ thời lượng gói.
      </p>
      {availability.alternatives.length ? (
        <div className="flex flex-wrap gap-2">
          {availability.alternatives.map((alternative) => (
            <button
              className="min-h-10 rounded-lg border border-amber-300 bg-white px-3 text-xs font-semibold hover:bg-amber-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700"
              key={alternative}
              onClick={() => onSelectAlternative(localInputValue(alternative))}
              type="button"
            >
              {relativeDateLabel(alternative)}
            </button>
          ))}
        </div>
      ) : null}
      {!replacement ? (
        <Button disabled={waiting} onClick={onWaitlist} variant="outline">
          {waiting ? "Đang thêm…" : "Nhận thông báo khi có chỗ"}
        </Button>
      ) : null}
    </div>
  );
}

export function AdvertisingBookingPanel({
  campaign,
  packageData,
  onClose,
  onPaid,
}: {
  campaign: AdvertisingCampaignSummary;
  packageData: AdvertisingPackage;
  onClose: () => void;
  onPaid: () => void;
}) {
  const queryClient = useQueryClient();
  const user = useAuthUser();
  const replacement = campaign.status === "NEEDS_RESCHEDULE";
  const storageKey = `advertising.checkout.${campaign.id}`;
  const [startLocal, setStartLocal] = useState(defaultStartValue);
  const [checkout, setCheckout] =
    useState<AdvertisingReservationCheckout | null>(null);
  const [confirmPayment, setConfirmPayment] = useState(false);
  const [feedback, setFeedback] = useState("");
  const startAt = isoValue(startLocal);
  const wallet = useQuery({
    queryKey: walletKey(user?.id),
    queryFn: walletApi.summary,
    enabled: Boolean(checkout),
  });
  const quote = useQuery({
    queryKey: ["advertising-quote", packageData.code],
    queryFn: () => advertisingApi.quote(packageData.code),
    enabled: !replacement,
    retry: false,
  });
  const availability = useQuery({
    queryKey: [
      "advertising-availability",
      campaign.id,
      packageData.code,
      startAt,
    ],
    queryFn: () =>
      advertisingApi.availability({
        placementCode: campaign.placementCode,
        packageCode: packageData.code,
        startAt: startAt!,
      }),
    enabled: Boolean(startAt && !checkout),
    retry: false,
  });

  useEffect(() => {
    let active = true;
    const savedId = window.sessionStorage.getItem(storageKey);
    if (!savedId)
      return () => {
        active = false;
      };
    void advertisingApi
      .getReservation(savedId)
      .then((saved) => {
        if (
          active &&
          saved.reservation.status === "HELD" &&
          saved.order.paymentStatus === "PENDING"
        ) {
          setCheckout(saved);
        } else {
          window.sessionStorage.removeItem(storageKey);
        }
      })
      .catch(() => window.sessionStorage.removeItem(storageKey));
    return () => {
      active = false;
    };
  }, [storageKey]);

  const reserve = useMutation({
    mutationFn: () => {
      if (!startAt) throw new Error("Ngày bắt đầu không hợp lệ.");
      const key = `ad-hold-${campaign.id}-${startAt}`;
      return advertisingApi.reserve(campaign.id, startAt, key);
    },
    onSuccess: (result) => {
      window.sessionStorage.setItem(storageKey, result.reservation.id);
      setCheckout(result);
      setFeedback("");
    },
    onError: (error) => {
      setFeedback(errorMessage(error));
      void availability.refetch();
    },
  });
  const waitlist = useMutation({
    mutationFn: () => {
      if (!startAt) throw new Error("Ngày bắt đầu không hợp lệ.");
      return advertisingApi.joinWaitlist(campaign.id, startAt);
    },
    onSuccess: async () => {
      setFeedback(
        "Đã thêm vào danh sách chờ. Chúng tôi sẽ báo khi lịch có chỗ.",
      );
      await queryClient.invalidateQueries({
        queryKey: ["advertising-waitlist"],
      });
    },
    onError: (error) => setFeedback(errorMessage(error)),
  });
  const reschedule = useMutation({
    mutationFn: () => {
      if (!startAt) throw new Error("Ngày bắt đầu không hợp lệ.");
      return advertisingApi.reschedule(campaign.id, startAt);
    },
    onSuccess: async () => {
      setFeedback("Đã cập nhật lịch chạy. Không phát sinh thanh toán mới.");
      await queryClient.invalidateQueries({
        queryKey: ["advertising-campaigns"],
      });
      onPaid();
    },
    onError: (error) => {
      setFeedback(errorMessage(error));
      void availability.refetch();
    },
  });
  const pay = useMutation({
    mutationFn: () => {
      if (!checkout) throw new Error("Không còn lượt giữ chỗ để thanh toán.");
      return advertisingApi.payOrder(
        checkout.order.id,
        `ad-payment-${checkout.order.id}`,
      );
    },
    onSuccess: async () => {
      window.sessionStorage.removeItem(storageKey);
      setCheckout(null);
      setConfirmPayment(false);
      setFeedback("Đã thanh toán. Lịch quảng cáo của bạn đã được xác nhận.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["advertising-campaigns"] }),
        queryClient.invalidateQueries({ queryKey: walletKey(user?.id) }),
      ]);
      onPaid();
    },
    onError: (error) => {
      setConfirmPayment(false);
      if (error instanceof ApiError && error.code.includes("EXPIRED")) {
        window.sessionStorage.removeItem(storageKey);
        setCheckout(null);
        setFeedback(
          "Lượt giữ chỗ đã hết hạn. Kiểm tra lại sức chứa để giữ lịch mới.",
        );
        void availability.refetch();
        return;
      }
      setFeedback(errorMessage(error));
    },
  });

  const handleStartChange = (event: ChangeEvent<HTMLInputElement>) => {
    setStartLocal(event.target.value);
    setFeedback("");
  };
  const available = availability.data?.available === true;
  const missingBalance = wallet.data
    ? Math.max(
        0,
        (checkout?.order.payableAmountVnd ?? 0) - wallet.data.balanceMinor,
      )
    : 0;

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--theme-border)] p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-50 text-primary-800">
            <CalendarDays aria-hidden="true" className="size-5" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-muted)]">
              {replacement
                ? "Điều chỉnh lịch đã thanh toán"
                : "Chọn ngày bắt đầu"}
            </p>
            <h2 className="mt-1 text-lg font-bold">{campaign.creativeTitle}</h2>
            <p className="mt-1 text-sm text-[var(--theme-muted)]">
              {campaign.placementName} · {packageData.name}
            </p>
          </div>
        </div>
        <Button onClick={onClose} variant="ghost">
          <ArrowLeft aria-hidden="true" className="size-4" /> Đóng
        </Button>
      </div>

      <div className="grid gap-5 p-4 sm:p-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="space-y-4">
          <label className="block max-w-sm space-y-1.5 text-sm font-semibold">
            <span>Ngày và giờ bắt đầu</span>
            <input
              className={fieldClassName}
              min={defaultStartValue()}
              onChange={handleStartChange}
              type="datetime-local"
              value={startLocal}
            />
          </label>
          <AvailabilityCard
            availability={availability.data}
            error={availability.error}
            isPending={availability.isPending}
            onSelectAlternative={setStartLocal}
            onWaitlist={() => waitlist.mutate()}
            replacement={replacement}
            selectedAt={startAt}
            waiting={waitlist.isPending}
          />
          {feedback ? (
            <p
              className="flex gap-2 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-3 text-sm leading-6"
              role="status"
            >
              <CircleAlert
                aria-hidden="true"
                className="mt-1 size-4 shrink-0"
              />
              {feedback}
            </p>
          ) : null}
          {checkout ? (
            <div className="space-y-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
              <p className="flex items-center gap-2 font-semibold">
                <Clock3 aria-hidden="true" className="size-4" /> Giữ chỗ đến{" "}
                {formatDateTime(checkout.reservation.expiresAt)}
              </p>
              <p>
                Số tiền cần thanh toán:{" "}
                <strong>{formatVnd(checkout.order.payableAmountVnd)}</strong>
              </p>
              <p className="leading-6">
                Thanh toán trước thời hạn để xác nhận lịch. Tiền chỉ bị trừ sau
                khi bạn xác nhận ở bước tiếp theo.
              </p>
              {wallet.data ? (
                <p>
                  Số dư ví:{" "}
                  <strong>{formatVnd(wallet.data.balanceMinor)}</strong>
                </p>
              ) : wallet.isPending ? (
                <p className="text-sm">Đang tải số dư ví…</p>
              ) : null}
              {missingBalance > 0 ? (
                <p className="font-semibold text-rose-800">
                  Cần nạp thêm {formatVnd(missingBalance)} để thanh toán.
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => setConfirmPayment(true)}>
                  <Wallet aria-hidden="true" className="size-4" /> Thanh toán
                  bằng ví
                </Button>
                {missingBalance > 0 ? (
                  <Link
                    className="inline-flex min-h-11 items-center rounded-xl border border-amber-300 bg-white px-4 text-sm font-semibold"
                    href="/wallet?returnTo=%2Fadvertising"
                  >
                    Nạp tiền vào ví
                  </Link>
                ) : null}
              </div>
            </div>
          ) : available ? (
            replacement ? (
              <Button
                disabled={reschedule.isPending}
                onClick={() => reschedule.mutate()}
              >
                {reschedule.isPending
                  ? "Đang cập nhật…"
                  : "Xác nhận lịch thay thế"}
              </Button>
            ) : (
              <Button
                disabled={reserve.isPending}
                onClick={() => reserve.mutate()}
              >
                {reserve.isPending ? "Đang giữ chỗ…" : "Giữ lịch 15 phút"}
              </Button>
            )
          ) : null}
        </div>

        <aside className="h-fit rounded-xl bg-[var(--theme-elevated)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-muted)]">
            Tóm tắt gói
          </p>
          <p className="mt-2 text-lg font-bold">{packageData.name}</p>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            {packageData.durationHours % 24 === 0
              ? `${packageData.durationHours / 24} ngày`
              : `${packageData.durationHours} giờ`}
          </p>
          {!replacement && quote.data ? (
            <p className="mt-4 border-t border-[var(--theme-border)] pt-4 text-sm">
              Thành tiền dự kiến
              <strong className="mt-1 block text-xl text-[var(--theme-text)]">
                {formatVnd(quote.data.payableAmountVnd)}
              </strong>
            </p>
          ) : null}
          {replacement ? (
            <p className="mt-4 border-t border-[var(--theme-border)] pt-4 text-sm leading-6 text-[var(--theme-muted)]">
              Chiến dịch đã thanh toán. Thay đổi lịch này không tạo khoản thu
              mới.
            </p>
          ) : null}
        </aside>
      </div>

      <ConfirmationDialog
        confirmLabel="Xác nhận trừ ví"
        description={`Hệ thống sẽ trừ ${checkout ? formatVnd(checkout.order.payableAmountVnd) : "số tiền của đơn"} từ ví nội bộ để xác nhận lịch quảng cáo.`}
        isPending={pay.isPending}
        onCancel={() => setConfirmPayment(false)}
        onConfirm={() => pay.mutate()}
        open={confirmPayment}
        title="Xác nhận thanh toán quảng cáo"
      >
        <p className="mt-3 text-sm text-[var(--theme-muted)]">
          Lịch giữ chỗ hết hạn lúc{" "}
          {checkout ? formatDateTime(checkout.reservation.expiresAt) : "—"}.
        </p>
      </ConfirmationDialog>
    </section>
  );
}
