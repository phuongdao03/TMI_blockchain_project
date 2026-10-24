"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Crown, Gem, HeartHandshake, LockKeyhole, MessageCircle, Send, Sparkles, Users } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { MembershipAvatar } from "@/components/ui/membership-avatar";
import { ApiError, membershipApi } from "@/lib/api/client";
import type { CommunityChatRoom, MembershipTier } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { membershipTiers } from "./member-card";

const ranks: Record<MembershipTier, number> = {
  MEMBER: 0,
  SILVER: 0,
  COMPANION: 1,
  PRESTIGE: 2,
};

export type { CommunityChatRoom } from "@/lib/api/types";

const rooms: {
  key: CommunityChatRoom;
  label: string;
  audience: string;
  icon: typeof Users;
}[] = [
  { key: "MEMBER", label: "Sảnh cộng đồng", audience: "Mọi hạng hội viên", icon: Users },
  { key: "COMPANION", label: "Phòng Đồng hành", audience: "Vàng trở lên", icon: HeartHandshake },
  { key: "PRESTIGE", label: "Phòng Tinh hoa", audience: "Kim cương", icon: Gem },
];
const roomRanks: Record<CommunityChatRoom, number> = {
  MEMBER: 0,
  COMPANION: 1,
  PRESTIGE: 2,
};

export function CommunityChat({
  tier,
  initialRoom = "MEMBER",
}: {
  tier: MembershipTier;
  initialRoom?: CommunityChatRoom;
}) {
  const [room, setRoom] = useState<CommunityChatRoom>(initialRoom);
  const [body, setBody] = useState("");
  const user = useAuthUser();
  const client = useQueryClient();
  const queryKey = ["membership-chat", user?.id, room];
  const access = useQuery({
    queryKey: ["membership-chat-access", user?.id, room],
    queryFn: () => membershipApi.chatAccess(room),
    enabled: Boolean(user?.id),
    staleTime: 30_000,
    retry: false,
  });
  const allowed = access.data?.allowed === true;
  const messages = useQuery({
    queryKey,
    queryFn: () => membershipApi.messages(room),
    enabled: allowed,
    refetchInterval: allowed ? 10_000 : false,
    retry: false,
  });
  const send = useMutation({
    mutationFn: () => membershipApi.send(room, body.trim()),
    onSuccess: (items) => {
      client.setQueryData(queryKey, items);
      setBody("");
    },
  });
  const remove = useMutation({
    mutationFn: membershipApi.removeMessage,
    onSuccess: () => client.invalidateQueries({ queryKey }),
  });
  return (
    <section
      id="community-chat"
      aria-labelledby="chat-heading"
      className="relative isolate scroll-mt-6 overflow-hidden rounded-[1.75rem] border border-amber-700/20 bg-gradient-to-br from-[var(--theme-surface)] via-[var(--theme-elevated)] to-[var(--theme-surface)] p-4 shadow-sm sm:p-7"
    >
      <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-20 -z-10 size-64 rounded-full bg-amber-400/10 blur-3xl" />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-amber-700/20 bg-amber-500/10 text-amber-700 shadow-sm sm:size-14">
            <Crown aria-hidden="true" className="size-6 sm:size-7" />
          </span>
          <div className="min-w-0">
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-amber-700">
              Không gian dành cho hội viên
            </p>
            <h2 id="chat-heading" className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl">
              {membershipTiers[room].room}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
              Chia sẻ câu chuyện, kết nối cùng cộng đồng trong một không gian riêng tư theo hạng hội viên.
            </p>
          </div>
        </div>
        <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-amber-700/20 bg-amber-500/10 px-3 text-xs font-semibold text-amber-800 dark:text-amber-200">
          {allowed ? <Sparkles aria-hidden="true" className="size-3.5" /> : <LockKeyhole aria-hidden="true" className="size-3.5" />}
          {allowed
            ? access.data?.source === "ADMIN"
              ? "Quyền quản trị · mọi phòng"
              : access.data?.source === "MANUAL"
                ? "Được cấp quyền riêng"
                : "Quyền theo hạng hội viên"
            : rooms.find((item) => item.key === room)?.audience}
        </span>
      </header>
      <nav aria-label="Các phòng hội viên" className="mt-6 grid gap-2 sm:grid-cols-3">
        {rooms.map((item) => {
          const Icon = item.icon;
          const selected = item.key === room;
          const isLocked = ranks[tier] < roomRanks[item.key] && !(selected && allowed) && access.data?.source !== "ADMIN";
          return (
            <button
              key={item.key}
              type="button"
              aria-pressed={selected}
              disabled={send.isPending}
              onClick={() => {
                setRoom(item.key);
                setBody("");
                send.reset();
                remove.reset();
              }}
              className={`flex min-h-[4.5rem] items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 ${selected ? "border-amber-600/50 bg-amber-500/10 shadow-sm" : "border-[var(--theme-border)] bg-[var(--theme-surface)] hover:border-amber-700/30 hover:bg-amber-500/5"}`}
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--theme-elevated)] text-amber-700">
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{item.label}</span>
                <span className="mt-0.5 block text-xs text-[var(--theme-muted)]">{item.audience}</span>
              </span>
              {isLocked ? <LockKeyhole aria-hidden="true" className="size-4 shrink-0 text-[var(--theme-muted)]" /> : null}
            </button>
          );
        })}
      </nav>
      <div className="mt-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]/80 p-3 sm:p-4">
      {!user?.id ? (
        <div role="status" className="flex min-h-36 flex-col items-center justify-center text-center">
          <LockKeyhole aria-hidden="true" className="size-6 text-amber-700" />
          <p className="mt-3 font-semibold">Đăng nhập để vào phòng</p>
        </div>
      ) : access.isPending ? (
        <div role="status" aria-label="Đang kiểm tra quyền vào phòng" className="space-y-3 py-4">
          <div className="h-4 w-40 animate-pulse rounded bg-[var(--theme-elevated)]" />
          <div className="h-16 animate-pulse rounded-xl bg-[var(--theme-elevated)]" />
          <div className="h-16 w-4/5 animate-pulse rounded-xl bg-[var(--theme-elevated)]" />
        </div>
      ) : access.isError ? (
        <div role="alert" className="flex min-h-36 flex-col items-center justify-center text-center">
          <p className="font-semibold">Chưa kiểm tra được quyền truy cập</p>
          <button className="mt-2 min-h-10 px-3 text-sm font-semibold text-amber-700 underline" onClick={() => void access.refetch()} type="button">
            Thử kiểm tra lại
          </button>
        </div>
      ) : !allowed ? (
        <div role="status" className="flex min-h-36 flex-col items-center justify-center rounded-xl bg-amber-500/5 px-4 text-center">
          <LockKeyhole aria-hidden="true" className="size-6 text-amber-700" />
          <h3 className="mt-3 font-semibold">Phòng này dành cho hạng {membershipTiers[room].name} trở lên</h3>
          <p className="mt-1 max-w-lg text-sm leading-6 text-[var(--theme-muted)]">
            Hạng hiện tại chưa mở phòng này. Xem các hạng hội viên và quyền lợi để chọn không gian phù hợp.
          </p>
          <a className="mt-3 inline-flex min-h-10 items-center font-semibold text-amber-700 underline" href="/cong-dong/hoi-vien">
            Xem hạng hội viên
          </a>
        </div>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2 px-1">
            <p className="text-sm font-semibold">Cuộc trò chuyện</p>
            <p className="text-xs text-[var(--theme-muted)]">50 tin gần nhất · tự làm mới mỗi 10 giây</p>
          </div>
          <div
            aria-label="Tin nhắn trong phòng"
            aria-live="polite"
            className="max-h-[30rem] min-h-48 space-y-3 overflow-y-auto overscroll-contain rounded-xl bg-[var(--theme-elevated)] p-3 sm:p-4"
          >
            {messages.isPending ? (
              <p role="status" className="py-8 text-center text-sm text-[var(--theme-muted)]">Đang tải cuộc trò chuyện…</p>
            ) : messages.isError ? (
              <p role="alert" className="py-8 text-center text-sm">
                Chưa thể tải cuộc trò chuyện. <button className="font-semibold text-amber-700 underline" onClick={() => void messages.refetch()} type="button">Thử lại</button>
              </p>
            ) : messages.data?.length === 0 ? (
              <div className="flex min-h-40 flex-col items-center justify-center text-center">
                <MessageCircle aria-hidden="true" className="size-7 text-amber-700/70" />
                <p className="mt-3 font-semibold">Phòng đang chờ câu chuyện đầu tiên</p>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">Gửi lời chào để bắt đầu kết nối với hội viên.</p>
              </div>
            ) : (
              messages.data?.map((message) => (
                <article
                  key={message.id}
                  className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 shadow-sm sm:p-4"
                >
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <MembershipAvatar
                      displayName={message.displayName}
                      src={message.avatarUrl}
                      size={36}
                      tier={message.tier}
                    />
                    <strong>{message.displayName}</strong>
                    <span className="rounded-full border border-amber-700/20 bg-amber-500/5 px-2.5 py-1 text-[0.68rem] font-semibold text-amber-800 dark:text-amber-200">
                      {membershipTiers[message.tier].name}
                    </span>
                    <time
                      className="ml-auto text-xs text-[var(--theme-muted)]"
                      dateTime={message.createdAt}
                    >
                      {new Date(message.createdAt).toLocaleTimeString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                    {message.canRemove && (
                      <button
                        className="min-h-9 px-2 text-xs font-semibold text-[var(--theme-muted)] underline"
                        disabled={remove.isPending}
                        onClick={() => remove.mutate(message.id)}
                        type="button"
                        aria-label={`Gỡ tin nhắn của ${message.displayName}`}
                      >
                        Gỡ
                      </button>
                    )}
                  </div>
                  {remove.isError && (
                    <p role="alert" className="text-red-700">
                      Chưa thể gỡ tin nhắn. Vui lòng thử lại.
                    </p>
                  )}
                  <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 sm:text-base">
                    {message.body}
                  </p>
                </article>
              ))
            )}
          </div>
          <form
            className="mt-4 flex flex-col gap-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-3 sm:flex-row sm:items-end sm:p-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (body.trim() && !send.isPending) send.mutate();
            }}
          >
            <label className="min-w-0 flex-1 text-xs font-semibold text-[var(--theme-muted)]" htmlFor="community-chat-body">
              Tin nhắn
              <textarea
                id="community-chat-body"
                className="mt-1.5 min-h-12 w-full resize-y rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-2.5 text-base font-normal leading-6 text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600"
                maxLength={2000}
                rows={2}
                placeholder="Chia sẻ câu chuyện của bạn…"
                value={body}
                onChange={(event) => setBody(event.target.value)}
                disabled={send.isPending}
              />
              <span className="mt-1 block text-right font-normal">{body.length}/2.000 ký tự</span>
            </label>
            <Button className="min-h-12 shrink-0 rounded-xl px-5" type="submit" disabled={!body.trim() || send.isPending}>
              <Send aria-hidden="true" className="size-4" />
              {send.isPending ? "Đang gửi…" : "Gửi tin nhắn"}
            </Button>
          </form>
          {send.isError && (
            <p role="alert" className="mt-3 text-red-700">
              {send.error instanceof ApiError
                ? send.error.message
                : "Chưa gửi được tin nhắn. Nội dung của bạn vẫn được giữ lại."}
            </p>
          )}
        </>
      )}
      </div>
    </section>
  );
}
