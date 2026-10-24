"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgeCheck, CalendarRange, ChartNoAxesCombined, Megaphone, Settings2 } from "lucide-react";
import { useState, type FormEvent } from "react";

import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { formatVnd } from "@/components/wallet/wallet-workspace";
import { advertisingApi } from "@/lib/api/client";
import type { AdvertisingReviewQueueItem } from "@/lib/api/types";

type AdminTab = "review" | "inventory" | "reports" | "catalog";
type Decision = "APPROVE" | "REJECT" | "CHANGES_REQUESTED" | "PAUSE";
type PendingDecision = { campaignId: string; decision: Decision; title: string };

const inputClassName =
  "min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary-500";

function localDate(value: Date): string {
  const date = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return date.toISOString().slice(0, 10);
}

function bound(value: string, end: boolean): string {
  return new Date(`${value}T${end ? "23:59:59" : "00:00:00"}`).toISOString();
}

function TabButton({
  active,
  children,
  icon: Icon,
  onClick,
}: {
  active: boolean;
  children: string;
  icon: typeof BadgeCheck;
  onClick: () => void;
}) {
  return (
    <button
      aria-selected={active}
      className={`inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-700 ${active ? "bg-primary-700 text-white" : "bg-[var(--theme-surface)] text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)]"}`}
      onClick={onClick}
      role="tab"
      type="button"
    >
      <Icon aria-hidden="true" className="size-4" /> {children}
    </button>
  );
}

function ReviewCard({
  item,
  onDecision,
}: {
  item: AdvertisingReviewQueueItem;
  onDecision: (decision: Decision, title: string) => void;
}) {
  return (
    <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[var(--theme-accent)]">{item.placementCode} · {item.packageName}</p>
          <h3 className="mt-1 text-lg font-bold">{item.title}</h3>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">{item.dossierCode} · {item.dossierTitle}</p>
        </div>
        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">{item.ownerEmail}</span>
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-6">{item.description}</p>
      <a className="mt-3 inline-flex min-h-10 items-center text-sm font-semibold text-primary-800 underline underline-offset-4" href={item.destinationUrl} rel="noreferrer" target="_blank">
        Mở liên kết đích
      </a>
      {item.imageUrl ? <p className="mt-1 break-all text-xs text-[var(--theme-muted)]">Ảnh: {item.imageUrl}</p> : null}
      <div className="mt-4 flex flex-wrap gap-2 border-t border-[var(--theme-border)] pt-4">
        <Button onClick={() => onDecision("APPROVE", item.title)}>
          <BadgeCheck aria-hidden="true" className="size-4" /> Duyệt nội dung
        </Button>
        <Button onClick={() => onDecision("CHANGES_REQUESTED", item.title)} variant="outline">Yêu cầu chỉnh sửa</Button>
        <Button onClick={() => onDecision("REJECT", item.title)} variant="ghost">Từ chối</Button>
      </div>
    </article>
  );
}

export function AdvertisingAdminWorkspace() {
  const queryClient = useQueryClient();
  const today = localDate(new Date());
  const twoWeeks = new Date();
  twoWeeks.setDate(twoWeeks.getDate() + 14);
  const [tab, setTab] = useState<AdminTab>("review");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(localDate(twoWeeks));
  const [decision, setDecision] = useState<PendingDecision | null>(null);
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState("");
  const [placementDrafts, setPlacementDrafts] = useState<Record<string, { capacity: number; enabled: boolean }>>({});
  const [packageDrafts, setPackageDrafts] = useState<Record<string, { basePriceVnd: number; active: boolean }>>({});
  const [placementForm, setPlacementForm] = useState({ code: "", name: "", pageLocation: "", capacity: 1 });
  const [packageForm, setPackageForm] = useState({ code: "", name: "", placementId: "", durationHours: 24, basePriceVnd: 100000 });

  const queue = useQuery({
    queryKey: ["advertising-review-queue"],
    queryFn: advertisingApi.reviewQueue,
    enabled: tab === "review",
  });
  const placements = useQuery({
    queryKey: ["advertising-admin-placements"],
    queryFn: advertisingApi.placements,
  });
  const packages = useQuery({
    queryKey: ["advertising-admin-packages"],
    queryFn: () => advertisingApi.packages(),
    enabled: tab === "catalog",
  });
  const inventory = useQuery({
    queryKey: ["advertising-admin-inventory", startDate, endDate],
    queryFn: () => advertisingApi.adminInventory(bound(startDate, false), bound(endDate, true)),
    enabled: tab === "inventory" && Boolean(startDate && endDate && startDate <= endDate),
  });
  const reports = useQuery({
    queryKey: ["advertising-admin-reports"],
    queryFn: advertisingApi.reports,
    enabled: tab === "reports",
  });

  const invalidateAll = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["advertising-review-queue"] }),
      queryClient.invalidateQueries({ queryKey: ["advertising-admin-inventory"] }),
      queryClient.invalidateQueries({ queryKey: ["advertising-admin-placements"] }),
      queryClient.invalidateQueries({ queryKey: ["advertising-admin-packages"] }),
      queryClient.invalidateQueries({ queryKey: ["advertising-placements"] }),
      queryClient.invalidateQueries({ queryKey: ["advertising-packages"] }),
    ]);
  };

  const reviewMutation = useMutation({
    mutationFn: async () => {
      if (!decision) return;
      if (decision.decision === "PAUSE") return advertisingApi.pauseCampaign(decision.campaignId, reason.trim());
      return advertisingApi.reviewCampaign(decision.campaignId, decision.decision, reason.trim() || undefined);
    },
    onSuccess: async () => {
      setFeedback("Đã cập nhật trạng thái chiến dịch.");
      setDecision(null);
      setReason("");
      await invalidateAll();
    },
    onError: () => setFeedback("Không thể cập nhật chiến dịch. Vui lòng thử lại."),
  });
  const placementMutation = useMutation({
    mutationFn: () => advertisingApi.createPlacement({
      code: placementForm.code.trim().toUpperCase().replaceAll(" ", "_"),
      name: placementForm.name.trim(),
      pageLocation: placementForm.pageLocation.trim(),
      deliveryMode: "EQUAL_ROTATION",
      capacity: Number(placementForm.capacity),
    }),
    onSuccess: async () => { setPlacementForm({ code: "", name: "", pageLocation: "", capacity: 1 }); await invalidateAll(); },
    onError: () => setFeedback("Không tạo được vị trí. Hãy kiểm tra mã vị trí có bị trùng không."),
  });
  const packageMutation = useMutation({
    mutationFn: () => advertisingApi.createPackage({
      code: packageForm.code.trim().toUpperCase().replaceAll(" ", "_"),
      name: packageForm.name.trim(),
      placementId: packageForm.placementId,
      durationHours: Number(packageForm.durationHours),
      rotationWeight: 1,
      basePriceVnd: Number(packageForm.basePriceVnd),
    }),
    onSuccess: async () => { setPackageForm({ code: "", name: "", placementId: "", durationHours: 24, basePriceVnd: 100000 }); await invalidateAll(); },
    onError: () => setFeedback("Không tạo được gói quảng cáo. Vui lòng kiểm tra thông tin."),
  });
  const updatePlacementMutation = useMutation({
    mutationFn: ({ id, ...input }: { id: string; capacity: number; enabled: boolean }) => advertisingApi.updatePlacement(id, input),
    onSuccess: invalidateAll,
    onError: () => setFeedback("Không cập nhật được cấu hình vị trí."),
  });
  const updatePackageMutation = useMutation({
    mutationFn: ({ id, ...input }: { id: string; basePriceVnd: number; active: boolean }) => advertisingApi.updatePackage(id, input),
    onSuccess: invalidateAll,
    onError: () => setFeedback("Không cập nhật được cấu hình gói."),
  });

  const openDecision = (campaignId: string, decisionValue: Decision, title: string) => {
    setReason("");
    setDecision({ campaignId, decision: decisionValue, title });
  };

  const submitPlacement = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); placementMutation.mutate(); };
  const submitPackage = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); packageMutation.mutate(); };

  return (
    <div className="space-y-6">
      <WorkspacePageHeader
        description="Duyệt nội dung, theo dõi công suất và cấu hình danh mục quảng cáo."
        icon={Megaphone}
        section="Vận hành"
        title="Quản trị quảng cáo"
      />

      <div aria-label="Các màn quản trị quảng cáo" className="flex flex-wrap gap-2" role="tablist">
        <TabButton active={tab === "review"} icon={BadgeCheck} onClick={() => setTab("review")}>Duyệt nội dung</TabButton>
        <TabButton active={tab === "inventory"} icon={CalendarRange} onClick={() => setTab("inventory")}>Lịch & công suất</TabButton>
        <TabButton active={tab === "reports"} icon={ChartNoAxesCombined} onClick={() => setTab("reports")}>Báo cáo</TabButton>
        <TabButton active={tab === "catalog"} icon={Settings2} onClick={() => setTab("catalog")}>Danh mục & giá</TabButton>
      </div>

      {feedback ? <p className="rounded-xl bg-[var(--theme-elevated)] p-3 text-sm" role="status">{feedback}</p> : null}

      {tab === "review" ? (
        <section aria-label="Hàng chờ duyệt" className="space-y-4">
          {queue.isPending ? <p className="rounded-xl bg-[var(--theme-surface)] p-5 text-sm" role="status">Đang tải nội dung chờ duyệt…</p> : null}
          {queue.isError ? <Button onClick={() => void queue.refetch()} variant="outline">Tải lại hàng chờ</Button> : null}
          {queue.data?.length === 0 ? <p className="rounded-xl border border-dashed border-[var(--theme-border)] bg-[var(--theme-surface)] p-8 text-center text-sm text-[var(--theme-muted)]">Không có nội dung đang chờ duyệt.</p> : null}
          {queue.data?.map((item) => <ReviewCard item={item} key={item.campaignId} onDecision={(value, title) => openDecision(item.campaignId, value, title)} />)}
        </section>
      ) : null}

      {tab === "inventory" ? (
        <section className="space-y-4">
          <div className="grid gap-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            <label className="space-y-1.5 text-sm font-semibold">Từ ngày<input className={inputClassName} onChange={(e) => setStartDate(e.target.value)} type="date" value={startDate} /></label>
            <label className="space-y-1.5 text-sm font-semibold">Đến ngày<input className={inputClassName} onChange={(e) => setEndDate(e.target.value)} type="date" value={endDate} /></label>
            <Button disabled={!startDate || !endDate || startDate > endDate} onClick={() => void inventory.refetch()} variant="outline">Cập nhật lịch</Button>
          </div>
          {inventory.isPending ? <p className="rounded-xl bg-[var(--theme-surface)] p-5 text-sm" role="status">Đang tải lịch quảng cáo…</p> : null}
          {inventory.isError ? <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-900" role="alert">Không tải được lịch và công suất.</p> : null}
          {inventory.data?.map((placement) => (
            <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5" key={placement.id}>
              <div className="flex flex-wrap justify-between gap-3">
                <div><h2 className="font-bold">{placement.name}</h2><p className="text-sm text-[var(--theme-muted)]">{placement.pageLocation} · công suất {placement.capacity}</p></div>
                <div className="flex gap-3 text-sm"><span>{placement.bookings.length} lịch đã đặt</span><span>{placement.reservations.length} lượt giữ chỗ</span></div>
              </div>
              <ul className="mt-4 divide-y divide-[var(--theme-border)]">
                {[...placement.bookings, ...placement.reservations].map((entry) => (
                  <li className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm" key={`${entry.id}-${entry.status}`}>
                    <div><p className="font-semibold">{entry.dossierTitle} · {entry.dossierCode}</p><p className="text-xs text-[var(--theme-muted)]">{entry.ownerEmail} · {new Date(entry.startAt).toLocaleString("vi-VN")} – {new Date(entry.endAt).toLocaleString("vi-VN")}</p></div>
                    <div className="flex items-center gap-2"><span className="rounded-full bg-[var(--theme-elevated)] px-3 py-1 text-xs">{entry.status}{entry.paymentStatus ? ` · ${entry.paymentStatus}` : ""}</span>{entry.status === "CONFIRMED" && entry.paymentStatus === "PAID" ? <Button className="min-h-9 px-3 py-1" onClick={() => openDecision(entry.campaignId, "PAUSE", entry.dossierTitle)} variant="outline">Tạm dừng</Button> : null}</div>
                  </li>
                ))}
                {placement.bookings.length + placement.reservations.length === 0 ? <li className="py-4 text-sm text-[var(--theme-muted)]">Chưa có lịch trong khoảng thời gian này.</li> : null}
              </ul>
            </article>
          ))}
        </section>
      ) : null}

      {tab === "reports" ? (
        <section className="space-y-4">
          {reports.isPending ? <p className="rounded-xl bg-[var(--theme-surface)] p-5 text-sm" role="status">Đang tổng hợp báo cáo…</p> : null}
          {reports.isError ? <p className="rounded-xl bg-rose-50 p-4 text-sm text-rose-900" role="alert">Không tải được báo cáo.</p> : null}
          {reports.data?.map((report) => (
            <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5" key={report.placementId}>
              <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-[var(--theme-accent)]">{report.placementCode}</p><h2 className="mt-1 text-lg font-bold">{report.placementName}</h2></div><p className="text-lg font-bold">{formatVnd(report.paidRevenueVnd)}</p></div>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">{[["Đơn đã thanh toán", report.paidOrders.toLocaleString("vi-VN")], ["Lượt phân phối", report.deliveryCount.toLocaleString("vi-VN")], ["Hiển thị hợp lệ", report.validImpressions.toLocaleString("vi-VN")], ["Tỷ lệ nhấp", `${(report.ctrBasisPoints / 100).toFixed(2)}%`]].map(([label, value]) => <div className="rounded-xl bg-[var(--theme-elevated)] p-3" key={label}><dt className="text-xs text-[var(--theme-muted)]">{label}</dt><dd className="mt-1 font-bold">{value}</dd></div>)}</dl>
              {report.campaigns.length ? <ul className="mt-4 divide-y divide-[var(--theme-border)]">{report.campaigns.map((campaign) => <li className="flex flex-wrap justify-between gap-2 py-2 text-sm" key={campaign.campaignId}><span>{campaign.title ?? campaign.campaignId}</span><span>{campaign.validClicks.toLocaleString("vi-VN")} nhấp · {(campaign.actualShareBasisPoints / 100).toFixed(1)}% lượt phân phối</span></li>)}</ul> : null}
            </article>
          ))}
        </section>
      ) : null}

      {tab === "catalog" ? (
        <section className="space-y-5">
          <div className="grid gap-5 xl:grid-cols-2">
            <form className="space-y-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4" onSubmit={submitPlacement}>
              <h2 className="font-bold">Thêm vị trí quảng cáo</h2>
              <label className="block space-y-1 text-sm">Mã vị trí<input className={inputClassName} onChange={(e) => setPlacementForm({ ...placementForm, code: e.target.value })} required value={placementForm.code} /></label>
              <label className="block space-y-1 text-sm">Tên hiển thị<input className={inputClassName} onChange={(e) => setPlacementForm({ ...placementForm, name: e.target.value })} required value={placementForm.name} /></label>
              <label className="block space-y-1 text-sm">Khu vực hiển thị<input className={inputClassName} onChange={(e) => setPlacementForm({ ...placementForm, pageLocation: e.target.value })} required value={placementForm.pageLocation} /></label>
              <label className="block space-y-1 text-sm">Suất tối đa cùng lúc<input className={inputClassName} min={1} onChange={(e) => setPlacementForm({ ...placementForm, capacity: Number(e.target.value) })} required type="number" value={placementForm.capacity} /></label>
              <Button disabled={placementMutation.isPending} type="submit">Tạo vị trí</Button>
            </form>
            <form className="space-y-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4" onSubmit={submitPackage}>
              <h2 className="font-bold">Thêm gói quảng cáo</h2>
              <label className="block space-y-1 text-sm">Mã gói<input className={inputClassName} onChange={(e) => setPackageForm({ ...packageForm, code: e.target.value })} required value={packageForm.code} /></label>
              <label className="block space-y-1 text-sm">Tên gói<input className={inputClassName} onChange={(e) => setPackageForm({ ...packageForm, name: e.target.value })} required value={packageForm.name} /></label>
              <label className="block space-y-1 text-sm">Vị trí<select className={inputClassName} onChange={(e) => setPackageForm({ ...packageForm, placementId: e.target.value })} required value={packageForm.placementId}><option value="">Chọn vị trí</option>{placements.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
              <div className="grid grid-cols-2 gap-3"><label className="block space-y-1 text-sm">Thời lượng (giờ)<input className={inputClassName} min={1} onChange={(e) => setPackageForm({ ...packageForm, durationHours: Number(e.target.value) })} required type="number" value={packageForm.durationHours} /></label><label className="block space-y-1 text-sm">Giá (VND)<input className={inputClassName} min={0} onChange={(e) => setPackageForm({ ...packageForm, basePriceVnd: Number(e.target.value) })} required type="number" value={packageForm.basePriceVnd} /></label></div>
              <Button disabled={packageMutation.isPending || !placements.data?.length} type="submit">Tạo gói</Button>
            </form>
          </div>
          <div className="grid gap-5 xl:grid-cols-2">
            <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"><h2 className="font-bold">Vị trí hiện có</h2>{placements.data?.map((placement) => { const draft = placementDrafts[placement.id] ?? { capacity: placement.capacity, enabled: placement.enabled }; return <div className="mt-3 grid gap-2 border-t border-[var(--theme-border)] pt-3 sm:grid-cols-[1fr_6rem_auto_auto] sm:items-end" key={placement.id}><div><p className="font-semibold">{placement.name}</p><p className="text-xs text-[var(--theme-muted)]">{placement.code} · {placement.pageLocation}</p></div><label className="text-xs">Công suất<input className={inputClassName} min={1} onChange={(e) => setPlacementDrafts({ ...placementDrafts, [placement.id]: { ...draft, capacity: Number(e.target.value) } })} type="number" value={draft.capacity} /></label><label className="flex min-h-11 items-center gap-2 text-sm"><input checked={draft.enabled} onChange={(e) => setPlacementDrafts({ ...placementDrafts, [placement.id]: { ...draft, enabled: e.target.checked } })} type="checkbox" />Đang mở</label><Button className="min-h-9 px-3 py-1" disabled={updatePlacementMutation.isPending} onClick={() => updatePlacementMutation.mutate({ id: placement.id, ...draft })} variant="outline">Lưu</Button></div>; })}</section>
            <section className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4"><h2 className="font-bold">Gói đang hoạt động</h2>{packages.isPending ? <p className="mt-3 text-sm">Đang tải gói…</p> : null}{packages.data?.map((item) => { const draft = packageDrafts[item.id] ?? { basePriceVnd: item.basePriceVnd, active: item.active }; return <div className="mt-3 grid gap-2 border-t border-[var(--theme-border)] pt-3 sm:grid-cols-[1fr_7rem_auto_auto] sm:items-end" key={item.id}><div><p className="font-semibold">{item.name}</p><p className="text-xs text-[var(--theme-muted)]">{item.code} · {item.durationHours} giờ</p></div><label className="text-xs">Giá (VND)<input className={inputClassName} min={0} onChange={(e) => setPackageDrafts({ ...packageDrafts, [item.id]: { ...draft, basePriceVnd: Number(e.target.value) } })} type="number" value={draft.basePriceVnd} /></label><label className="flex min-h-11 items-center gap-2 text-sm"><input checked={draft.active} onChange={(e) => setPackageDrafts({ ...packageDrafts, [item.id]: { ...draft, active: e.target.checked } })} type="checkbox" />Đang mở</label><Button className="min-h-9 px-3 py-1" onClick={() => updatePackageMutation.mutate({ id: item.id, ...draft })} variant="outline">Lưu</Button></div>; })}</section>
          </div>
        </section>
      ) : null}

      <ConfirmationDialog
        confirmDisabled={Boolean(decision && decision.decision !== "APPROVE" && !reason.trim())}
        confirmLabel={decision?.decision === "APPROVE" ? "Duyệt chiến dịch" : decision?.decision === "PAUSE" ? "Tạm dừng" : decision?.decision === "REJECT" ? "Từ chối nội dung" : "Gửi yêu cầu chỉnh sửa"}
        description={decision?.decision === "APPROVE" ? `Duyệt nội dung “${decision.title}” để chủ hồ sơ có thể đặt lịch.` : decision?.decision === "PAUSE" ? `Tạm dừng phân phối “${decision.title}”. Nhập lý do để lưu vào lịch sử.` : `Gửi quyết định cho “${decision?.title ?? "chiến dịch"}”. Hãy nhập lý do để chủ hồ sơ biết cần xử lý thế nào.`}
        isPending={reviewMutation.isPending}
        onCancel={() => setDecision(null)}
        onConfirm={() => reviewMutation.mutate()}
        open={Boolean(decision)}
        title={decision?.decision === "APPROVE" ? "Xác nhận duyệt" : decision?.decision === "PAUSE" ? "Tạm dừng chiến dịch" : "Gửi phản hồi duyệt"}
      >
        {decision && decision.decision !== "APPROVE" ? <label className="mt-4 block space-y-1.5 text-sm font-semibold">Lý do<textarea className={`${inputClassName} min-h-24 py-2`} onChange={(e) => setReason(e.target.value)} value={reason} /></label> : null}
      </ConfirmationDialog>
    </div>
  );
}
