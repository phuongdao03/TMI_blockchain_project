"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Pencil, Plus, Send, XCircle } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { communityEventsApi } from "@/lib/api/client";
import type { CommunityEvent, CommunityEventEntitlement, CommunityEventInput, MembershipTier } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

type EventForm = Omit<CommunityEventInput, "startsAt" | "endsAt" | "cancellationCutoffAt" | "registrationOpensAt" | "priorityOpensAt"> & {
  startsAt: string;
  endsAt: string;
  cancellationCutoffAt: string;
  registrationOpensAt: string;
  priorityOpensAt: string;
};

const emptyForm: EventForm = {
  title: "", description: "", startsAt: "", endsAt: "", location: "",
  registrationOpensAt: "", priorityTier: null, priorityOpensAt: "",
  requiredTier: "MEMBER", capacity: 30, ticketPriceMinor: 0,
  cancellationCutoffAt: "", includedEntitlement: null, entitlementQuota: null,
  requiresDiamondApproval: false,
};
const tiers: Array<[MembershipTier, string]> = [
  ["MEMBER", "Đồng (miễn phí)"], ["SILVER", "Bạc"],
  ["COMPANION", "Vàng"], ["PRESTIGE", "Kim cương"],
];

function localDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}
function dateLabel(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function AdminEventsWorkspace() {
  const user = useAuthUser();
  const client = useQueryClient();
  const allowed = Boolean(user?.roles.includes("SUPER_ADMIN") || user?.permissions?.includes("memberships.manage"));
  const [page, setPage] = useState(1);
  const events = useQuery({
    queryKey: ["admin-community-events", page],
    queryFn: () => communityEventsApi.adminList(page),
    enabled: allowed,
  });
  const [form, setForm] = useState<EventForm>(emptyForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmCancelId, setConfirmCancelId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const reload = async () => Promise.all([
    client.invalidateQueries({ queryKey: ["admin-community-events"] }),
    client.invalidateQueries({ queryKey: ["community-events"] }),
  ]);
  const save = useMutation({
    mutationFn: (input: CommunityEventInput) => editingId
      ? communityEventsApi.update(editingId, input)
      : communityEventsApi.create(input),
    onSuccess: async () => { setForm(emptyForm); setEditingId(null); setFormError(null); await reload(); },
    onError: () => setFormError("Không lưu được sự kiện. Kiểm tra ngày giờ, sức chứa và điều kiện Kim cương."),
  });
  const publish = useMutation({ mutationFn: communityEventsApi.publish, onSuccess: reload });
  const cancel = useMutation({ mutationFn: communityEventsApi.cancel, onSuccess: async () => { setConfirmCancelId(null); await reload(); } });
  const inputClass = "mt-2 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base";
  const eventRows = events.data?.data.events ?? [];
  const pageCount = Math.max(
    1,
    Math.ceil((events.data?.meta.total ?? 0) / (events.data?.meta.pageSize ?? 20)),
  );

  function update<K extends keyof EventForm>(key: K, value: EventForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }
  function beginEdit(event: CommunityEvent) {
    setEditingId(event.id);
    setForm({
      title: event.title, description: event.description,
      startsAt: localDate(event.startsAt), endsAt: localDate(event.endsAt),
      registrationOpensAt: event.registrationOpensAt ? localDate(event.registrationOpensAt) : "",
      priorityTier: event.priorityTier,
      priorityOpensAt: event.priorityOpensAt ? localDate(event.priorityOpensAt) : "",
      location: event.location, requiredTier: event.requiredTier,
      capacity: event.capacity, ticketPriceMinor: event.ticketPriceMinor,
      cancellationCutoffAt: event.cancellationCutoffAt ? localDate(event.cancellationCutoffAt) : "",
      includedEntitlement: event.includedEntitlement, entitlementQuota: event.entitlementQuota,
      requiresDiamondApproval: event.requiresDiamondApproval,
    });
    setFormError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const input: CommunityEventInput = {
        ...form,
        startsAt: new Date(form.startsAt).toISOString(),
        endsAt: new Date(form.endsAt).toISOString(),
        registrationOpensAt: form.registrationOpensAt ? new Date(form.registrationOpensAt).toISOString() : null,
        priorityTier: form.priorityTier,
        priorityOpensAt: form.priorityTier && form.priorityOpensAt ? new Date(form.priorityOpensAt).toISOString() : null,
        cancellationCutoffAt: form.cancellationCutoffAt ? new Date(form.cancellationCutoffAt).toISOString() : null,
      };
      setFormError(null);
      save.mutate(input);
    } catch {
      setFormError("Vui lòng nhập thời gian hợp lệ.");
    }
  }

  if (!allowed) return <p role="alert">Tài khoản chưa có quyền quản lý sự kiện.</p>;
  return (
    <main className="mx-auto max-w-6xl space-y-8 pb-10">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-sm font-semibold uppercase tracking-wide text-[var(--theme-accent)]">Quản trị hội viên</p><h1 className="mt-2 text-3xl font-bold sm:text-4xl">Sự kiện cộng đồng</h1><p className="mt-2 max-w-2xl leading-7 text-[var(--theme-muted)]">Tạo sự kiện, đặt điều kiện hạng thẻ, hạn mức quyền lợi và quản lý công bố.</p></div>
        <Link className="inline-flex min-h-11 items-center font-semibold text-[var(--theme-accent)] underline" href="/events">Xem trang hội viên</Link>
      </header>

      <form className="grid gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:grid-cols-2 sm:p-7" onSubmit={submit}>
        <div className="sm:col-span-2"><h2 className="text-xl font-bold">{editingId ? "Chỉnh sửa sự kiện" : "Tạo sự kiện"}</h2><p className="mt-1 text-sm text-[var(--theme-muted)]">Sự kiện mới được lưu ở trạng thái nháp cho đến khi công bố.</p></div>
        <label className="text-sm font-semibold sm:col-span-2">Tên sự kiện<input className={inputClass} required maxLength={200} value={form.title} onChange={(e) => update("title", e.target.value)} /></label>
        <label className="text-sm font-semibold sm:col-span-2">Mô tả<textarea className={`${inputClass} min-h-28 py-3`} required maxLength={20000} value={form.description} onChange={(e) => update("description", e.target.value)} /></label>
        <label className="text-sm font-semibold">Bắt đầu<input className={inputClass} required type="datetime-local" value={form.startsAt} onChange={(e) => update("startsAt", e.target.value)} /></label>
        <label className="text-sm font-semibold">Kết thúc<input className={inputClass} required type="datetime-local" value={form.endsAt} onChange={(e) => update("endsAt", e.target.value)} /></label>
        <label className="text-sm font-semibold">Mở đăng ký chung<input className={inputClass} required={Boolean(form.priorityTier)} type="datetime-local" value={form.registrationOpensAt} onChange={(e) => update("registrationOpensAt", e.target.value)} /><span className="mt-1 block text-xs font-normal text-[var(--theme-muted)]">Để trống nếu mở đăng ký chung ngay khi công bố.</span></label>
        <label className="text-sm font-semibold">Hạng được đăng ký ưu tiên<select className={inputClass} value={form.priorityTier ?? ""} onChange={(e) => { const value = e.target.value as "COMPANION" | "PRESTIGE" | ""; update("priorityTier", value || null); if (!value) update("priorityOpensAt", ""); }}><option value="">Không bật ưu tiên</option><option value="COMPANION" disabled={form.requiredTier === "PRESTIGE"}>Vàng trở lên</option><option value="PRESTIGE">Kim cương</option></select></label>
        <label className="text-sm font-semibold sm:col-span-2">Mở đăng ký ưu tiên<input className={inputClass} required={Boolean(form.priorityTier)} disabled={!form.priorityTier} type="datetime-local" value={form.priorityOpensAt} onChange={(e) => update("priorityOpensAt", e.target.value)} /><span className="mt-1 block text-xs font-normal text-[var(--theme-muted)]">Hội viên thuộc hạng ưu tiên được đăng ký từ thời điểm này đến khi mở đăng ký chung.</span></label>
        <label className="text-sm font-semibold sm:col-span-2">Địa điểm<input className={inputClass} required maxLength={300} value={form.location} onChange={(e) => update("location", e.target.value)} /></label>
        <label className="text-sm font-semibold">Hạng thẻ tối thiểu<select className={inputClass} value={form.requiredTier} onChange={(e) => update("requiredTier", e.target.value as MembershipTier)}>{tiers.map(([tier, label]) => <option key={tier} value={tier} disabled={(form.requiresDiamondApproval || form.includedEntitlement === "CIRCLE") && tier !== "PRESTIGE"}>{label}</option>)}</select></label>
        <label className="text-sm font-semibold">Sức chứa<input className={inputClass} required type="number" min={1} max={100000} step={1} value={form.capacity} onChange={(e) => update("capacity", Number(e.target.value))} /></label>
        <label className="text-sm font-semibold">Giá vé (VNĐ)<input className={inputClass} required type="number" min={0} max={1000000000} step={1} value={form.ticketPriceMinor} onChange={(e) => update("ticketPriceMinor", Number(e.target.value))} /><span className="mt-1 block text-xs font-normal text-[var(--theme-muted)]">Vé có phí hiện chưa kết nối thanh toán trực tuyến.</span></label>
        <label className="text-sm font-semibold">Hạn hủy đăng ký<input className={inputClass} type="datetime-local" value={form.cancellationCutoffAt} onChange={(e) => update("cancellationCutoffAt", e.target.value)} /></label>
        <label className="text-sm font-semibold">Quyền lợi được dùng<select className={inputClass} value={form.includedEntitlement ?? ""} onChange={(e) => {
          const value = e.target.value as CommunityEventEntitlement | "";
          update("includedEntitlement", value || null);
          update("entitlementQuota", value ? (form.entitlementQuota ?? 1) : null);
          if (value === "CIRCLE") { update("requiredTier", "PRESTIGE"); update("requiresDiamondApproval", true); }
        }}><option value="">Không áp dụng</option><option value="TALK">Talk</option><option value="CONNECT">Connect</option><option value="CIRCLE">Circle</option></select></label>
        <label className="text-sm font-semibold">Số lượt trừ theo mỗi đăng ký<input className={inputClass} type="number" min={1} max={100000} step={1} disabled={!form.includedEntitlement} value={form.entitlementQuota ?? ""} onChange={(e) => update("entitlementQuota", e.target.value ? Number(e.target.value) : null)} /></label>
        <label className="flex min-h-11 items-center gap-3 text-sm font-semibold sm:col-span-2"><input className="size-5 accent-sky-700" type="checkbox" checked={form.requiresDiamondApproval} disabled={form.includedEntitlement === "CIRCLE"} onChange={(e) => { update("requiresDiamondApproval", e.target.checked); if (e.target.checked) update("requiredTier", "PRESTIGE"); }} />Chỉ hội viên Kim cương đã được duyệt mới đủ điều kiện</label>
        {formError ? <p className="text-sm text-red-700 sm:col-span-2" role="alert">{formError}</p> : null}
        <div className="flex flex-wrap gap-3 sm:col-span-2"><Button disabled={save.isPending} type="submit"><Plus aria-hidden="true" className="size-4" />{save.isPending ? "Đang lưu…" : editingId ? "Lưu thay đổi" : "Tạo bản nháp"}</Button>{editingId ? <Button type="button" variant="outline" onClick={() => { setEditingId(null); setForm(emptyForm); setFormError(null); }}>Hủy chỉnh sửa</Button> : null}</div>
      </form>

      <section aria-labelledby="admin-event-list-title" className="space-y-4">
        <h2 className="text-xl font-bold" id="admin-event-list-title">Sự kiện đã tạo</h2>
        {events.isPending ? <p role="status">Đang tải danh sách…</p> : null}
        {events.isError ? <div><p role="alert">Chưa tải được danh sách sự kiện.</p><Button className="mt-3" onClick={() => void events.refetch()}>Thử lại</Button></div> : null}
        {eventRows.map((item) => <AdminEventRow key={item.id} event={item} busy={publish.isPending || cancel.isPending} confirming={confirmCancelId === item.id} onEdit={() => beginEdit(item)} onPublish={() => publish.mutate(item.id)} onAskCancel={() => setConfirmCancelId(item.id)} onCancel={() => cancel.mutate(item.id)} onKeep={() => setConfirmCancelId(null)} />)}
        {!events.isPending && !events.isError && eventRows.length === 0 ? <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-7 text-center text-[var(--theme-muted)]">Chưa có sự kiện nào.</p> : null}
        {pageCount > 1 ? <nav aria-label="Trang quản trị sự kiện" className="flex items-center justify-center gap-4"><Button disabled={page <= 1} onClick={() => setPage((current) => current - 1)} variant="outline">Trước</Button><span className="text-sm text-[var(--theme-muted)]">Trang {page} / {pageCount}</span><Button disabled={page >= pageCount} onClick={() => setPage((current) => current + 1)} variant="outline">Sau</Button></nav> : null}
      </section>
    </main>
  );
}

function AdminEventRow({ event, busy, confirming, onEdit, onPublish, onAskCancel, onCancel, onKeep }: {
  event: CommunityEvent; busy: boolean; confirming: boolean; onEdit: () => void;
  onPublish: () => void; onAskCancel: () => void; onCancel: () => void; onKeep: () => void;
}) {
  return (
    <article className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h3 className="text-lg font-bold">{event.title}</h3><span className="rounded-full border px-2.5 py-1 text-xs font-bold">{event.status === "DRAFT" ? "Bản nháp" : event.status === "PUBLISHED" ? "Đã công bố" : "Đã hủy"}</span></div><p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-[var(--theme-muted)]"><CalendarDays aria-hidden="true" className="size-4" />{dateLabel(event.startsAt)} · {event.confirmedCount}/{event.capacity} chỗ · {event.requiredTier === "PRESTIGE" ? "Kim cương" : event.requiredTier === "COMPANION" ? "Vàng" : event.requiredTier === "SILVER" ? "Bạc" : "Đồng"}+</p></div>
        <div className="flex flex-wrap gap-2">{event.status !== "CANCELLED" ? <Button disabled={busy} onClick={onEdit} variant="outline"><Pencil aria-hidden="true" className="size-4" />Sửa</Button> : null}{event.status === "DRAFT" ? <Button disabled={busy} onClick={onPublish}><Send aria-hidden="true" className="size-4" />Công bố</Button> : null}{event.status === "PUBLISHED" ? <Button disabled={busy} onClick={onAskCancel} variant="outline"><XCircle aria-hidden="true" className="size-4" />Hủy sự kiện</Button> : null}</div>
      </div>
      {confirming ? <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-4"><p className="text-sm font-semibold text-amber-950">Hủy sự kiện này sẽ hủy các đăng ký hiện có.</p><div className="mt-3 flex gap-2"><Button disabled={busy} onClick={onCancel}>Xác nhận hủy</Button><Button disabled={busy} onClick={onKeep} variant="outline">Giữ sự kiện</Button></div></div> : null}
    </article>
  );
}
