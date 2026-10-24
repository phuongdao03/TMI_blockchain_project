"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChartNoAxesCombined, Megaphone, RotateCw } from "lucide-react";
import { useState } from "react";

import { AdvertisingBookingPanel } from "@/components/advertising/advertising-booking-panel";
import { AdvertisingCampaignList } from "@/components/advertising/advertising-campaign-list";
import { AdvertisingCreativeEditPanel } from "@/components/advertising/advertising-creative-edit-panel";
import { AdvertisingSetupPanel } from "@/components/advertising/advertising-setup-panel";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { Button } from "@/components/ui/button";
import { advertisingApi } from "@/lib/api/client";

function dateLabel(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdvertisingWorkspace({
  initialDossierId,
}: {
  initialDossierId?: string;
}) {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(Boolean(initialDossierId));
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(
    null,
  );
  const [editingCampaignId, setEditingCampaignId] = useState<string | null>(
    null,
  );
  const [metricsCampaignId, setMetricsCampaignId] = useState<string | null>(
    null,
  );
  const campaigns = useQuery({
    queryKey: ["advertising-campaigns"],
    queryFn: advertisingApi.campaigns,
  });
  const selectedCampaign = campaigns.data?.find(
    (campaign) => campaign.id === selectedCampaignId,
  );
  const editingCampaign = campaigns.data?.find(
    (campaign) => campaign.id === editingCampaignId,
  );
  const packages = useQuery({
    queryKey: ["advertising-packages", selectedCampaign?.placementCode],
    queryFn: () => advertisingApi.packages(selectedCampaign!.placementCode),
    enabled: Boolean(selectedCampaign),
  });
  const selectedPackage = packages.data?.find(
    (item) => item.id === selectedCampaign?.packageId,
  );
  const metrics = useQuery({
    queryKey: ["advertising-metrics", metricsCampaignId],
    queryFn: () => advertisingApi.metrics(metricsCampaignId!),
    enabled: Boolean(metricsCampaignId),
  });
  const waitlist = useQuery({
    queryKey: ["advertising-waitlist"],
    queryFn: advertisingApi.listWaitlist,
  });
  const cancelWaitlist = useMutation({
    mutationFn: advertisingApi.cancelWaitlist,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["advertising-waitlist"],
      });
    },
  });

  const closeBooking = () => setSelectedCampaignId(null);
  const refreshCampaigns = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["advertising-campaigns"],
    });
  };

  return (
    <div className="space-y-6">
      <WorkspacePageHeader
        description="Chuẩn bị nội dung, chọn vị trí và theo dõi lịch phân phối quảng cáo cho hồ sơ của bạn."
        icon={Megaphone}
        section="Truyền thông hồ sơ"
        title="Quảng cáo của tôi"
        action={
          !creating ? (
            <Button onClick={() => setCreating(true)}>
              <Megaphone aria-hidden="true" className="size-4" /> Tạo chiến dịch
            </Button>
          ) : undefined
        }
      />

      {selectedCampaign ? (
        selectedPackage ? (
          <AdvertisingBookingPanel
            campaign={selectedCampaign}
            onClose={closeBooking}
            onPaid={() => void refreshCampaigns()}
            packageData={selectedPackage}
          />
        ) : packages.isPending ? (
          <p
            className="rounded-xl bg-[var(--theme-surface)] p-5 text-sm text-[var(--theme-muted)]"
            role="status"
          >
            Đang tải thông tin gói quảng cáo…
          </p>
        ) : (
          <section
            className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-950"
            role="alert"
          >
            Không tìm thấy gói của chiến dịch này. Vui lòng tải lại hoặc liên hệ
            quản trị viên.
            <Button className="ml-3" onClick={closeBooking} variant="outline">
              Đóng
            </Button>
          </section>
        )
      ) : null}

      {creating ? (
        <section className="space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--theme-accent)]">
                Bước 1 · Nội dung
              </p>
              <h2 className="mt-1 text-xl font-bold">Tạo chiến dịch</h2>
            </div>
            <Button onClick={() => setCreating(false)} variant="ghost">
              Đóng
            </Button>
          </div>
          <AdvertisingSetupPanel
            initialDossierId={initialDossierId}
            onCreated={() => {
              setCreating(false);
              void refreshCampaigns();
            }}
          />
        </section>
      ) : null}

      {editingCampaign ? (
        <AdvertisingCreativeEditPanel
          campaign={editingCampaign}
          key={editingCampaign.id}
          onDone={() => {
            setEditingCampaignId(null);
            void refreshCampaigns();
          }}
          onClose={() => setEditingCampaignId(null)}
        />
      ) : null}

      {campaigns.isPending ? (
        <p
          className="rounded-xl bg-[var(--theme-surface)] p-5 text-sm text-[var(--theme-muted)]"
          role="status"
        >
          Đang tải chiến dịch…
        </p>
      ) : campaigns.isError ? (
        <div
          className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-900"
          role="alert"
        >
          Không tải được chiến dịch. Kiểm tra kết nối rồi thử lại.
          <Button
            className="ml-3"
            onClick={() => void campaigns.refetch()}
            variant="outline"
          >
            <RotateCw aria-hidden="true" className="size-4" /> Thử lại
          </Button>
        </div>
      ) : (
        <AdvertisingCampaignList
          campaigns={campaigns.data ?? []}
          onCreateCampaign={() => setCreating(true)}
          onEditCreative={setEditingCampaignId}
          onScheduleCampaign={setSelectedCampaignId}
          onShowMetrics={setMetricsCampaignId}
        />
      )}

      {waitlist.data?.length ? (
        <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
          <h2 className="font-bold">Lịch đang chờ chỗ</h2>
          <ul className="mt-3 divide-y divide-[var(--theme-border)]">
            {waitlist.data.map((entry) => (
              <li
                className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm"
                key={entry.id}
              >
                <div>
                  <p className="font-semibold">
                    {dateLabel(entry.startAt)} ·{" "}
                    {entry.status === "WAITING"
                      ? "Đang chờ"
                      : entry.status === "NOTIFIED"
                        ? "Đã có chỗ"
                        : entry.status === "FULFILLED"
                          ? "Đã đặt lịch"
                          : "Đã hủy"}
                  </p>
                  <p className="text-xs text-[var(--theme-muted)]">
                    Thời lượng yêu cầu đến {dateLabel(entry.endAt)}
                  </p>
                </div>
                {entry.status === "WAITING" || entry.status === "NOTIFIED" ? (
                  <Button
                    disabled={cancelWaitlist.isPending}
                    onClick={() => cancelWaitlist.mutate(entry.id)}
                    variant="outline"
                  >
                    Hủy yêu cầu
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {metricsCampaignId ? (
        <section
          className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5"
          aria-live="polite"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <ChartNoAxesCombined
                aria-hidden="true"
                className="size-5 text-[var(--theme-accent)]"
              />
              <div>
                <h2 className="font-bold">Hiệu quả chiến dịch</h2>
                <p className="text-xs text-[var(--theme-muted)]">
                  Bắt đầu {dateLabel(selectedCampaign?.actualStartAt ?? null)}
                </p>
              </div>
            </div>
            <Button onClick={() => setMetricsCampaignId(null)} variant="ghost">
              Đóng
            </Button>
          </div>
          {metrics.isPending ? (
            <p className="mt-4 text-sm text-[var(--theme-muted)]">
              Đang tổng hợp…
            </p>
          ) : null}
          {metrics.isError ? (
            <p className="mt-4 text-sm text-rose-800" role="alert">
              Chưa tải được báo cáo.
            </p>
          ) : null}
          {metrics.data ? (
            <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                [
                  "Lượt phân phối",
                  metrics.data.deliveryCount.toLocaleString("vi-VN"),
                ],
                [
                  "Lượt hiển thị hợp lệ",
                  metrics.data.validImpressions.toLocaleString("vi-VN"),
                ],
                [
                  "Lượt nhấp hợp lệ",
                  metrics.data.validClicks.toLocaleString("vi-VN"),
                ],
                [
                  "Tỷ lệ nhấp",
                  `${(metrics.data.ctrBasisPoints / 100).toFixed(2)}%`,
                ],
              ].map(([label, value]) => (
                <div
                  className="rounded-xl bg-[var(--theme-elevated)] p-4"
                  key={label}
                >
                  <dt className="text-xs text-[var(--theme-muted)]">{label}</dt>
                  <dd className="mt-1 text-xl font-bold">{value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
