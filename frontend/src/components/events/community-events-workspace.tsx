"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, MapPin, RotateCw, TicketCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, communityEventsApi } from "@/lib/api/client";
import type { CommunityEvent, CommunityEventRegistrationStatus, MembershipTier } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";

const tierNames: Record<MembershipTier, string> = {
  MEMBER: "Đồng", SILVER: "Bạc", COMPANION: "Vàng", PRESTIGE: "Kim cương",
};
const registrationLabels: Partial<Record<CommunityEventRegistrationStatus, string>> = {
  CONFIRMED: "Đã xác nhận", WAITLISTED: "Đang trong danh sách chờ",
  CANCELLED: "Đã hủy", CANCELLED_LATE: "Đã hủy sau hạn",
  CANCELLED_BY_EVENT: "Sự kiện đã hủy", INELIGIBLE: "Chưa đủ điều kiện",
  PAYMENT_REQUIRED: "Cần thanh toán vé",
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "long", timeStyle: "short" }).format(new Date(value));
}
function formatPrice(amount: number) {
  return amount === 0 ? "Miễn phí" : new Intl.NumberFormat("vi-VN", {
    style: "currency", currency: "VND", maximumFractionDigits: 0,
  }).format(amount);
}
function actionError(error: unknown) {
  if (error instanceof ApiError && error.status === 402) return "Sự kiện cần thanh toán vé; thanh toán trực tuyến chưa được kết nối.";
  if (error instanceof ApiError && error.status === 403) return "Hạng thẻ hoặc trạng thái xét duyệt hiện tại chưa đủ điều kiện.";
  if (error instanceof ApiError && error.code === "EVENT_REGISTRATION_NOT_OPEN") return "Chưa đến thời điểm mở đăng ký cho hạng hội viên của bạn.";
  if (error instanceof ApiError && error.status === 409) return "Sự kiện vừa thay đổi. Hãy tải lại danh sách.";
  return "Không thể cập nhật đăng ký. Vui lòng thử lại.";
}
function entitlementLabel(event: CommunityEvent) {
  if (!event.includedEntitlement) return null;
  const names = { TALK: "Talk", CONNECT: "Connect", CIRCLE: "Circle" };
  return `Dùng ${event.entitlementQuota ?? 1} lượt ${names[event.includedEntitlement]}`;
}

export function CommunityEventsWorkspace() {
  const user = useAuthUser();
  const client = useQueryClient();
  const [eventPage, setEventPage] = useState(1);
  const events = useQuery({
    queryKey: ["community-events", eventPage],
    queryFn: () => communityEventsApi.list(eventPage),
    staleTime: 30_000,
  });
  const registrations = useQuery({
    queryKey: ["community-event-registrations", user?.id],
    queryFn: communityEventsApi.myRegistrations,
    enabled: Boolean(user),
  });
  const refresh = async () => Promise.all([
    client.invalidateQueries({ queryKey: ["community-events"] }),
    client.invalidateQueries({ queryKey: ["community-event-registrations"] }),
  ]);
  const register = useMutation({ mutationFn: communityEventsApi.register, onSuccess: refresh });
  const cancel = useMutation({ mutationFn: communityEventsApi.cancelRegistration, onSuccess: refresh });
  const myRegistrations = registrations.data?.registrations ?? [];
  const registrationByEvent = new Map<string, (typeof myRegistrations)[number]["registration"]>();
  for (const item of myRegistrations) {
    if (!registrationByEvent.has(item.event.id)) {
      registrationByEvent.set(item.event.id, item.registration);
    }
  }
  const eventRows = events.data?.data.events ?? [];
  const eventPageCount = Math.max(
    1,
    Math.ceil((events.data?.meta.total ?? 0) / (events.data?.meta.pageSize ?? 20)),
  );

  return (
    <main className="mx-auto max-w-6xl space-y-7 pb-10">
      <header className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.12em] text-[var(--theme-accent)]">Tinh Hoa Việt · Kết nối trực tiếp</p>
        <div className="mt-2 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Sự kiện cộng đồng</h1>
            <p className="mt-3 max-w-2xl leading-7 text-[var(--theme-muted)]">
              Khám phá các buổi gặp gỡ, tọa đàm và hoạt động dành cho hội viên. Quyền tham gia được kiểm tra theo hạng thẻ và lượt sử dụng còn lại.
            </p>
          </div>
          <Link className="inline-flex min-h-11 items-center font-semibold text-[var(--theme-accent)] underline" href="/membership">Xem quyền lợi hội viên</Link>
        </div>
      </header>

      {register.error || cancel.error ? <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-900">{actionError(register.error ?? cancel.error)}</p> : null}
      {events.isPending ? <p role="status">Đang tải lịch sự kiện…</p> : null}
      {events.isError ? <div className="rounded-xl border border-[var(--theme-border)] p-5"><p role="alert">Chưa thể tải lịch sự kiện.</p><Button className="mt-3" onClick={() => void events.refetch()}><RotateCw aria-hidden="true" className="size-4" /> Thử lại</Button></div> : null}
      <section aria-labelledby="my-event-registrations" className="space-y-3">
        <h2 className="text-xl font-bold" id="my-event-registrations">Đăng ký của tôi</h2>
        {registrations.isPending ? <p role="status">Đang tải đăng ký…</p> : null}
        {registrations.isError ? <p role="alert">Chưa thể tải lịch sử đăng ký.</p> : null}
        {!registrations.isPending && !registrations.isError && myRegistrations.length === 0 ? <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-5 text-sm text-[var(--theme-muted)]">Bạn chưa có đăng ký sự kiện nào.</p> : null}
        {myRegistrations.map(({ registration, event }) => <article key={registration.id} className="flex flex-col gap-2 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:flex-row sm:items-center sm:justify-between"><div className="min-w-0"><h3 className="font-semibold">{event.title}</h3><p className="mt-1 text-sm text-[var(--theme-muted)]">{formatDate(event.startsAt)} · {event.location}</p></div><span className="shrink-0 rounded-full border border-[var(--theme-border)] px-3 py-1.5 text-sm font-semibold">{registrationLabels[registration.status] ?? registration.status}</span></article>)}
      </section>
      {!events.isPending && eventRows.length === 0 ? <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-8 text-center text-[var(--theme-muted)]">Chưa có sự kiện nào được công bố. Hãy quay lại sau.</p> : null}
      <section aria-label="Danh sách sự kiện" className="grid gap-4 md:grid-cols-2">
        {eventRows.map((event) => {
          const registration = registrationByEvent.get(event.id);
          const active = registration?.status === "CONFIRMED" || registration?.status === "WAITLISTED";
          const paid = event.ticketPriceMinor > 0 && !event.includedEntitlement;
          return (
            <article key={event.id} className="flex min-w-0 flex-col rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div><p className="text-xs font-bold uppercase tracking-wide text-[var(--theme-accent)]">Dành cho hội viên {tierNames[event.requiredTier]} trở lên</p><h2 className="mt-2 text-xl font-bold leading-snug">{event.title}</h2></div>
                <span className="shrink-0 rounded-full border border-[var(--theme-border)] px-3 py-1 text-sm font-semibold">{formatPrice(event.ticketPriceMinor)}</span>
              </div>
              <p className="mt-4 whitespace-pre-line text-sm leading-6 text-[var(--theme-muted)]">{event.description}</p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div className="flex min-w-0 items-start gap-2"><CalendarDays aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-[var(--theme-accent)]" /><div><dt className="font-semibold">Thời gian</dt><dd className="mt-1">{formatDate(event.startsAt)}</dd></div></div>
                <div className="flex min-w-0 items-start gap-2"><MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-[var(--theme-accent)]" /><div><dt className="font-semibold">Địa điểm</dt><dd className="mt-1 break-words">{event.location}</dd></div></div>
                {event.registrationOpensAt ? <div className="sm:col-span-2"><dt className="font-semibold">Mở đăng ký chung</dt><dd className="mt-1 text-[var(--theme-muted)]">{formatDate(event.registrationOpensAt)}</dd></div> : null}
              </dl>
              <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
                <span className="rounded-full bg-[var(--theme-muted)]/10 px-3 py-1.5">Còn {Math.max(0, event.capacity - event.confirmedCount)} / {event.capacity} chỗ</span>
                {event.includedEntitlement ? <span className="rounded-full bg-emerald-100 px-3 py-1.5 text-emerald-950">{entitlementLabel(event)}</span> : null}
                {event.requiresDiamondApproval ? <span className="rounded-full bg-sky-100 px-3 py-1.5 text-sky-950">Cần duyệt Kim cương</span> : null}
              </div>
              {event.priorityTier && event.priorityOpensAt ? <p className="mt-3 rounded-lg bg-emerald-50 p-3 text-sm leading-5 text-emerald-950">Hội viên {tierNames[event.priorityTier]} trở lên được đăng ký ưu tiên từ {formatDate(event.priorityOpensAt)}.</p> : null}
              {event.ticketPriceMinor > 0 && event.includedEntitlement ? <p className="mt-3 text-xs leading-5 text-[var(--theme-muted)]">Có thể dùng lượt {event.includedEntitlement} còn lại; khi hết lượt, cần thanh toán vé.</p> : null}
              {registration ? <p className="mt-4 flex items-center gap-2 text-sm font-semibold" role="status"><TicketCheck aria-hidden="true" className="size-4 text-emerald-700" />{registrationLabels[registration.status] ?? registration.status}{registration.entitlementUnits > 0 ? ` · Đã dùng ${registration.entitlementUnits} lượt ${registration.entitlementSnapshot}` : ""}</p> : null}
              <div className="mt-auto flex flex-wrap items-center gap-3 pt-5">
                {active ? <Button disabled={cancel.isPending} onClick={() => cancel.mutate(event.id)} variant="outline">Hủy đăng ký</Button> : paid ? <Button disabled title="Chưa có bước thanh toán vé trực tuyến">Cần thanh toán vé</Button> : <Button disabled={register.isPending || event.status !== "PUBLISHED"} onClick={() => register.mutate(event.id)}>{register.isPending ? "Đang đăng ký…" : "Đăng ký tham gia"}</Button>}
                {paid ? <span className="text-xs leading-5 text-[var(--theme-muted)]">Thanh toán vé trực tuyến chưa được kết nối.</span> : null}
              </div>
            </article>
          );
        })}
      </section>
      {eventPageCount > 1 ? <nav aria-label="Trang sự kiện" className="flex items-center justify-center gap-4"><Button disabled={eventPage <= 1} onClick={() => setEventPage((page) => page - 1)} variant="outline">Trước</Button><span className="text-sm text-[var(--theme-muted)]">Trang {eventPage} / {eventPageCount}</span><Button disabled={eventPage >= eventPageCount} onClick={() => setEventPage((page) => page + 1)} variant="outline">Sau</Button></nav> : null}
    </main>
  );
}
