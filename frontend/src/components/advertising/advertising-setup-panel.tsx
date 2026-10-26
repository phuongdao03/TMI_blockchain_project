"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  LoaderCircle,
  Megaphone,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";

import { AdvertisingPlacementPreview } from "@/components/advertising/advertising-placement-preview";
import { Button } from "@/components/ui/button";
import { formatVnd } from "@/components/wallet/wallet-workspace";
import { advertisingApi, ApiError, dossierApi } from "@/lib/api/client";
import type {
  AdvertisingCampaignCreated,
  AdvertisingPackage,
  Dossier,
} from "@/lib/api/types";

const inputClassName =
  "min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)] outline-none transition focus-visible:ring-2 focus-visible:ring-primary-500";

const blockedDossierStatuses = new Set([
  "DRAFT",
  "REJECTED",
  "REVOKED",
  "CANCELLED",
]);

function durationLabel(hours: number): string {
  if (hours % 24 === 0) return `${hours / 24} ngày`;
  return `${hours} giờ`;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Không thể gửi yêu cầu. Vui lòng thử lại.";
}

export function AdvertisingSetupPanel({
  initialDossierId,
  onCreated,
}: {
  initialDossierId?: string;
  onCreated: () => void;
}) {
  const queryClient = useQueryClient();
  const dossiers = useQuery({
    queryKey: ["advertising-eligible-dossiers"],
    queryFn: () => dossierApi.list({ page: 1, pageSize: 100 }),
  });
  const placements = useQuery({
    queryKey: ["advertising-placements"],
    queryFn: advertisingApi.placements,
  });
  const catalog = useQuery({
    queryKey: ["advertising-package-catalog"],
    queryFn: () => advertisingApi.packages(),
  });
  const eligibleDossiers = useMemo(
    () =>
      dossiers.data?.data.filter(
        (dossier) => !blockedDossierStatuses.has(dossier.status),
      ) ?? [],
    [dossiers.data?.data],
  );
  const [dossierId, setDossierId] = useState(initialDossierId ?? "");
  const [placementCode, setPlacementCode] = useState("");
  const selectedDossierId = eligibleDossiers.some(
    (item) => item.id === dossierId,
  )
    ? dossierId
    : (eligibleDossiers.find((item) => item.id === initialDossierId)?.id ??
      eligibleDossiers[0]?.id ??
      "");
  const selectedPlacementCode =
    placementCode ||
    placements.data?.find((placement) =>
      catalog.data?.some((plan) => plan.placementId === placement.id),
    )?.code ||
    placements.data?.[0]?.code ||
    "";
  const packages = useQuery({
    queryKey: ["advertising-packages", selectedPlacementCode],
    queryFn: () => advertisingApi.packages(selectedPlacementCode),
    enabled: Boolean(selectedPlacementCode),
  });
  const [packageCode, setPackageCode] = useState("");
  const selectedPackage =
    packages.data?.find((item) => item.code === packageCode) ??
    packages.data?.[0];
  const selectedPackageCode = selectedPackage?.code ?? "";
  const quote = useQuery({
    queryKey: ["advertising-quote", selectedPackageCode],
    queryFn: () => advertisingApi.quote(selectedPackageCode),
    enabled: Boolean(selectedPackageCode),
    retry: false,
  });
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [destinationUrl, setDestinationUrl] = useState("");
  const [savedDraft, setSavedDraft] = useState<{
    campaignId: string;
    message: string;
  } | null>(null);

  const createCampaign = useMutation({
    mutationFn: async (input: {
      dossierId: string;
      packageCode: string;
      title: string;
      description: string;
      imageUrl: string | null;
      destinationUrl: string;
    }) => {
      const created: AdvertisingCampaignCreated =
        await advertisingApi.createCampaign(input);
      try {
        await advertisingApi.submitCampaign(created.campaign.id);
        return { campaignId: created.campaign.id, submitted: true as const };
      } catch (error) {
        return {
          campaignId: created.campaign.id,
          submitted: false as const,
          error: errorMessage(error),
        };
      }
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({
        queryKey: ["advertising-campaigns"],
      });
      if (result.submitted) {
        setSavedDraft(null);
        setTitle("");
        setDescription("");
        setImageUrl("");
        setDestinationUrl("");
        onCreated();
      } else {
        setSavedDraft({
          campaignId: result.campaignId,
          message: result.error,
        });
      }
    },
  });

  const retrySubmit = useMutation({
    mutationFn: (campaignId: string) =>
      advertisingApi.submitCampaign(campaignId),
    onSuccess: async () => {
      setSavedDraft(null);
      await queryClient.invalidateQueries({
        queryKey: ["advertising-campaigns"],
      });
      onCreated();
    },
  });

  const isLoading =
    dossiers.isPending || placements.isPending || catalog.isPending;
  const loadError = dossiers.error ?? placements.error;
  const selectedPlacement = placements.data?.find(
    (placement) => placement.code === selectedPlacementCode,
  );
  const canSubmit = Boolean(
    selectedDossierId &&
      selectedPackage &&
      title.trim().length >= 2 &&
      destinationUrl.trim() &&
      quote.data,
  );

  if (isLoading) {
    return (
      <div
        aria-busy="true"
        className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6"
        role="status"
      >
        <span className="flex items-center gap-3 text-sm font-semibold text-[var(--theme-muted)]">
          <LoaderCircle
            aria-hidden="true"
            className="thv-loading-spinner size-5"
          />
          Đang tải hồ sơ và vị trí quảng cáo…
        </span>
      </div>
    );
  }

  if (loadError) {
    return (
      <div
        className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900"
        role="alert"
      >
        Không thể tải dữ liệu quảng cáo. Vui lòng tải lại trang hoặc thử lại
        sau.
      </div>
    );
  }

  if (!eligibleDossiers.length) {
    return (
      <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 sm:p-8">
        <span className="grid size-12 place-items-center rounded-xl bg-primary-50 text-primary-800">
          <BadgeCheck aria-hidden="true" className="size-6" />
        </span>
        <h2 className="mt-4 text-xl font-bold">Cần có hồ sơ đủ điều kiện</h2>
        <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--theme-muted)]">
          Bạn có thể chuẩn bị chiến dịch trước khi hồ sơ được công bố. Hồ sơ bản
          nháp, bị từ chối, thu hồi hoặc đã hủy chưa thể gắn với quảng cáo.
        </p>
        <Link
          className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-[var(--theme-border)] px-4 text-sm font-semibold"
          href="/dossiers"
        >
          Xem hồ sơ của tôi <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </section>
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPackage || !canSubmit) return;
    setSavedDraft(null);
    createCampaign.mutate({
      dossierId: selectedDossierId,
      packageCode: selectedPackage.code,
      title: title.trim(),
      description: description.trim(),
      imageUrl: imageUrl.trim() || null,
      destinationUrl: destinationUrl.trim(),
    });
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
      <form className="space-y-5 py-2 xl:pr-6" onSubmit={handleSubmit}>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--theme-accent)]">
            Thiết lập chiến dịch
          </p>
          <h2 className="mt-1 text-xl font-bold">Chọn hồ sơ và vị trí</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
            Nội dung sẽ được kiểm duyệt trước khi bạn chọn lịch và thanh toán.
          </p>
        </div>

        <label className="block space-y-1.5 text-sm font-semibold">
          <span>Hồ sơ muốn quảng bá</span>
          <select
            className={inputClassName}
            onChange={(event) => setDossierId(event.target.value)}
            value={selectedDossierId}
          >
            {eligibleDossiers.map((dossier: Dossier) => (
              <option key={dossier.id} value={dossier.id}>
                {dossier.title} · {dossier.code}
              </option>
            ))}
          </select>
          <span className="block text-xs font-normal text-[var(--theme-muted)]">
            Hồ sơ chưa công bố có thể chuẩn bị chiến dịch; quảng cáo chỉ phân
            phối sau khi hồ sơ được công khai.
          </span>
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5 text-sm font-semibold">
            <span>Vị trí hiển thị</span>
            <select
              className={inputClassName}
              onChange={(event) => {
                setPlacementCode(event.target.value);
                setPackageCode("");
              }}
              value={selectedPlacementCode}
            >
              {placements.data?.map((placement) => (
                <option key={placement.id} value={placement.code}>
                  {placement.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1.5 text-sm font-semibold">
            <span>Gói thời lượng</span>
            <select
              className={inputClassName}
              disabled={!packages.data?.length}
              onChange={(event) => setPackageCode(event.target.value)}
              value={selectedPackageCode}
            >
              {!packages.data?.length ? (
                <option value="">
                  {packages.isPending
                    ? "Đang tải thời lượng…"
                    : packages.isError
                      ? "Không tải được gói thời lượng"
                      : "Chưa có gói cho vị trí này"}
                </option>
              ) : null}
              {packages.data?.map((item: AdvertisingPackage) => (
                <option key={item.id} value={item.code}>
                  {item.name} · {durationLabel(item.durationHours)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {selectedPlacement ? (
          <details className="border-y border-[var(--theme-border)] py-3">
            <summary className="cursor-pointer text-sm font-semibold">
              Xem vị trí quảng cáo trên trang · {selectedPlacement.name}
            </summary>
            <div className="mt-3">
              <AdvertisingPlacementPreview placement={selectedPlacement} />
            </div>
          </details>
        ) : null}

        {selectedPlacement && !packages.isPending && !packages.data?.length ? (
          <p
            className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950"
            role="status"
          >
            Vị trí này chưa có gói đang mở. Vui lòng chọn vị trí khác hoặc liên
            hệ quản trị viên.
          </p>
        ) : null}

        <div className="grid gap-4">
          <label className="block space-y-1.5 text-sm font-semibold">
            <span>Tên nội dung quảng cáo</span>
            <input
              className={inputClassName}
              maxLength={120}
              onChange={(event) => setTitle(event.target.value)}
              required
              value={title}
            />
          </label>
          <label className="block space-y-1.5 text-sm font-semibold">
            <span>Mô tả ngắn</span>
            <textarea
              className={`${inputClassName} min-h-24 resize-y py-3`}
              maxLength={500}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
              value={description}
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block space-y-1.5 text-sm font-semibold">
              <span>Ảnh quảng cáo (không bắt buộc)</span>
              <input
                className={inputClassName}
                onChange={(event) => setImageUrl(event.target.value)}
                placeholder="https://..."
                type="url"
                value={imageUrl}
              />
            </label>
            <label className="block space-y-1.5 text-sm font-semibold">
              <span>Liên kết đích</span>
              <input
                className={inputClassName}
                inputMode="url"
                maxLength={2048}
                onChange={(event) => setDestinationUrl(event.target.value)}
                placeholder="https://... hoặc /cong-dong"
                required
                value={destinationUrl}
              />
            </label>
          </div>
        </div>

        {quote.error ? (
          <div
            className="flex gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
            role="alert"
          >
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0"
            />
            Không thể tính báo giá. Vui lòng chọn lại gói hoặc thử lại.
          </div>
        ) : null}
        {createCampaign.error ? (
          <p
            className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
            role="alert"
          >
            {errorMessage(createCampaign.error)}
          </p>
        ) : null}
        {savedDraft ? (
          <div
            className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950"
            role="status"
          >
            <p className="font-semibold">
              Đã lưu chiến dịch nhưng chưa gửi được để duyệt.
            </p>
            <p className="mt-1 leading-6">{savedDraft.message}</p>
            <Button
              className="mt-3"
              disabled={retrySubmit.isPending}
              onClick={() => retrySubmit.mutate(savedDraft.campaignId)}
              variant="outline"
            >
              {retrySubmit.isPending ? "Đang gửi…" : "Gửi duyệt lại"}
            </Button>
          </div>
        ) : null}

        <div className="flex flex-col-reverse gap-3 border-t border-[var(--theme-border)] pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs leading-5 text-[var(--theme-muted)]">
            Chưa trừ tiền ở bước này. Bạn sẽ chọn lịch và xác nhận thanh toán
            sau khi được duyệt.
          </p>
          <Button
            className="shrink-0"
            disabled={!canSubmit || createCampaign.isPending}
            type="submit"
          >
            {createCampaign.isPending
              ? "Đang gửi…"
              : "Tạo chiến dịch và gửi duyệt"}
            <ArrowRight aria-hidden="true" className="size-4" />
          </Button>
        </div>
      </form>

      <aside className="space-y-4">
        <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-primary-50 text-primary-800">
              <Megaphone aria-hidden="true" className="size-5" />
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-muted)]">
                Dự kiến thanh toán
              </p>
              <p className="mt-0.5 text-2xl font-bold tracking-tight text-[var(--theme-text)]">
                {quote.data ? formatVnd(quote.data.payableAmountVnd) : "—"}
              </p>
            </div>
          </div>
          {quote.data ? (
            <dl className="mt-5 space-y-3 border-t border-[var(--theme-border)] pt-4 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--theme-muted)]">Giá gói</dt>
                <dd className="font-semibold">
                  {formatVnd(quote.data.baseAmountVnd)}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--theme-muted)]">
                  Ưu đãi hạng {quote.data.membershipTier}
                </dt>
                <dd className="font-semibold text-emerald-800">
                  −{formatVnd(quote.data.discountAmountVnd)}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--theme-muted)]">Thời lượng</dt>
                <dd className="font-semibold">
                  {durationLabel(quote.data.durationHours)}
                </dd>
              </div>
            </dl>
          ) : quote.isPending && selectedPackageCode ? (
            <p className="mt-4 text-sm text-[var(--theme-muted)]" role="status">
              Đang tính ưu đãi thành viên…
            </p>
          ) : null}
          <p className="mt-4 rounded-xl bg-[var(--theme-elevated)] p-3 text-xs leading-5 text-[var(--theme-muted)]">
            Báo giá được tính từ gói và quyền lợi thành viên hiện tại. Số tiền
            chính thức sẽ được khóa khi bạn giữ lịch.
          </p>
        </section>

        <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6">
          <h3 className="font-bold">Quy trình từ đây</h3>
          <ol className="mt-4 space-y-3 text-sm">
            <li className="flex gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full bg-primary-50 text-xs font-bold text-primary-800">
                1
              </span>
              <span>Nội dung được quản trị viên xét duyệt.</span>
            </li>
            <li className="flex gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full border border-[var(--theme-border)] text-xs font-bold">
                2
              </span>
              <span>Chọn ngày bắt đầu và kiểm tra chỗ trống.</span>
            </li>
            <li className="flex gap-3">
              <span className="grid size-6 shrink-0 place-items-center rounded-full border border-[var(--theme-border)] text-xs font-bold">
                3
              </span>
              <span>Xác nhận trừ ví để kích hoạt lịch đã giữ.</span>
            </li>
          </ol>
        </section>
      </aside>
    </div>
  );
}
