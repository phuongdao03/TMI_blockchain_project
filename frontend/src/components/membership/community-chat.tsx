"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Crown,
  Gem,
  HeartHandshake,
  LockKeyhole,
  MessageCircle,
  Pencil,
  Send,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { MembershipAvatar } from "@/components/ui/membership-avatar";
import { ApiError, membershipApi } from "@/lib/api/client";
import type {
  CommunityChatMessage,
  CommunityChatPage,
  CommunityChatRoom,
  MembershipTier,
} from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import { membershipTiers } from "./member-card";

const ranks: Record<MembershipTier, number> = {
  MEMBER: 0,
  SILVER: 0,
  COMPANION: 1,
  PRESTIGE: 2,
};

export type { CommunityChatRoom } from "@/lib/api/types";

type ChatHistoryData = {
  pages: CommunityChatPage[];
  pageParams: (string | null)[];
};

const rooms: {
  key: CommunityChatRoom;
  label: string;
  audience: string;
  icon: typeof Users;
}[] = [
  {
    key: "MEMBER",
    label: "Sảnh cộng đồng",
    audience: "Mọi hạng hội viên",
    icon: Users,
  },
  {
    key: "COMPANION",
    label: "Phòng Đồng hành",
    audience: "Vàng trở lên",
    icon: HeartHandshake,
  },
  {
    key: "PRESTIGE",
    label: "Phòng Tinh hoa",
    audience: "Kim cương",
    icon: Gem,
  },
];
const roomRanks: Record<CommunityChatRoom, number> = {
  MEMBER: 0,
  COMPANION: 1,
  PRESTIGE: 2,
};

function mergeChatMessages(
  existing: CommunityChatMessage[],
  incoming: CommunityChatMessage[],
) {
  const byId = new Map(existing.map((message) => [message.id, message]));
  for (const message of incoming) {
    const current = byId.get(message.id);
    if (
      current?.editedAt &&
      (!message.editedAt ||
        new Date(message.editedAt).getTime() <
          new Date(current.editedAt).getTime())
    ) {
      continue;
    }
    byId.set(message.id, message);
  }
  return [...byId.values()].sort(
    (left, right) =>
      left.createdAt.localeCompare(right.createdAt) ||
      left.id.localeCompare(right.id),
  );
}

function mergeLatestPage(
  data: ChatHistoryData | undefined,
  latest: CommunityChatPage,
): ChatHistoryData {
  if (!data) return { pages: [latest], pageParams: [null] };
  return {
    ...data,
    pages: data.pages.map((page, index) =>
      index === 0
        ? { ...page, items: mergeChatMessages(page.items, latest.items) }
        : page,
    ),
  };
}

export function CommunityChat({
  tier,
  initialRoom = "MEMBER",
}: {
  tier: MembershipTier;
  initialRoom?: CommunityChatRoom;
}) {
  const [room, setRoom] = useState<CommunityChatRoom>(initialRoom);
  const [body, setBody] = useState("");
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [removedMessageIds, setRemovedMessageIds] = useState<Set<string>>(
    () => new Set(),
  );
  const user = useAuthUser();
  const client = useQueryClient();
  const historyKey = useMemo(
    () => ["membership-chat-history", user?.id, room],
    [room, user?.id],
  );
  const latestKey = [...historyKey, "latest"];
  const access = useQuery({
    queryKey: ["membership-chat-access", user?.id, room],
    queryFn: () => membershipApi.chatAccess(room),
    enabled: Boolean(user?.id),
    staleTime: 30_000,
    retry: false,
  });
  const allowed = access.data?.allowed === true;
  const history = useInfiniteQuery({
    queryKey: historyKey,
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      membershipApi.messages(room, { cursor: pageParam, limit: 50 }),
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: allowed,
    retry: false,
  });
  const latest = useQuery({
    queryKey: latestKey,
    queryFn: () => membershipApi.messages(room, { limit: 50 }),
    enabled: allowed && history.isSuccess,
    refetchInterval: allowed && history.isSuccess ? 10_000 : false,
    retry: false,
  });
  useEffect(() => {
    if (!latest.data) return;
    const filteredPage = {
      ...latest.data,
      items: latest.data.items.filter(
        (message) => !removedMessageIds.has(message.id),
      ),
    };
    client.setQueryData<ChatHistoryData>(historyKey, (current) =>
      mergeLatestPage(current, filteredPage),
    );
  }, [client, historyKey, latest.data, removedMessageIds]);
  const send = useMutation({
    mutationFn: () => membershipApi.send(room, body.trim()),
    onSuccess: (message) => {
      const page: CommunityChatPage = {
        items: [message],
        hasMore: false,
        nextCursor: null,
      };
      client.setQueryData<ChatHistoryData>(historyKey, (current) =>
        mergeLatestPage(current, page),
      );
      client.setQueryData<CommunityChatPage>(latestKey, (current) => ({
        items: mergeChatMessages(current?.items ?? [], [message]),
        hasMore: current?.hasMore ?? false,
        nextCursor: current?.nextCursor ?? null,
      }));
      setBody("");
    },
  });
  const edit = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      membershipApi.editMessage(id, body),
    onSuccess: (updated) => {
      client.setQueryData<ChatHistoryData>(historyKey, (current) =>
        current
          ? {
              ...current,
              pages: current.pages.map((page) => ({
                ...page,
                items: page.items.map((message) =>
                  message.id === updated.id ? updated : message,
                ),
              })),
            }
          : current,
      );
      client.setQueryData<CommunityChatPage>(latestKey, (current) =>
        current
          ? {
              ...current,
              items: current.items.map((message) =>
                message.id === updated.id ? updated : message,
              ),
            }
          : current,
      );
      setEditingMessageId(null);
      setEditBody("");
    },
  });
  const remove = useMutation({
    mutationFn: membershipApi.removeMessage,
    onSuccess: (_result, id) => {
      setRemovedMessageIds((current) => new Set(current).add(id));
      client.setQueryData<ChatHistoryData>(historyKey, (current) =>
        current
          ? {
              ...current,
              pages: current.pages.map((page) => ({
                ...page,
                items: page.items.filter((message) => message.id !== id),
              })),
            }
          : current,
      );
      client.setQueryData<CommunityChatPage>(latestKey, (current) =>
        current
          ? {
              ...current,
              items: current.items.filter((message) => message.id !== id),
            }
          : current,
      );
    },
  });
  const messagesById = new Map<string, CommunityChatMessage>();
  for (const page of [...(history.data?.pages ?? [])].reverse()) {
    for (const message of page.items) {
      if (!removedMessageIds.has(message.id)) {
        messagesById.set(message.id, message);
      }
    }
  }
  const renderedMessages = [...messagesById.values()].sort(
    (left, right) =>
      left.createdAt.localeCompare(right.createdAt) ||
      left.id.localeCompare(right.id),
  );
  return (
    <section
      id="community-chat"
      aria-labelledby="chat-heading"
      className="relative isolate scroll-mt-6 overflow-hidden rounded-[1.75rem] border border-amber-700/20 bg-gradient-to-br from-[var(--theme-surface)] via-[var(--theme-elevated)] to-[var(--theme-surface)] p-4 shadow-sm sm:p-7"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-12 -top-20 -z-10 size-64 rounded-full bg-amber-400/10 blur-3xl"
      />
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-4">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-amber-700/20 bg-amber-500/10 text-amber-700 shadow-sm sm:size-14">
            <Crown aria-hidden="true" className="size-6 sm:size-7" />
          </span>
          <div className="min-w-0">
            <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-amber-700">
              Không gian dành cho hội viên
            </p>
            <h2
              id="chat-heading"
              className="mt-1 text-2xl font-bold tracking-tight sm:text-3xl"
            >
              {membershipTiers[room].room}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-[var(--theme-muted)]">
              Chia sẻ câu chuyện, kết nối cùng cộng đồng trong một không gian
              riêng tư theo hạng hội viên.
            </p>
          </div>
        </div>
        <span className="inline-flex min-h-9 items-center gap-2 rounded-full border border-amber-700/20 bg-amber-500/10 px-3 text-xs font-semibold text-amber-800 dark:text-amber-200">
          {allowed ? (
            <Sparkles aria-hidden="true" className="size-3.5" />
          ) : (
            <LockKeyhole aria-hidden="true" className="size-3.5" />
          )}
          {allowed
            ? access.data?.source === "ADMIN"
              ? "Quyền quản trị · mọi phòng"
              : access.data?.source === "MANUAL"
                ? "Được cấp quyền riêng"
                : "Quyền theo hạng hội viên"
            : rooms.find((item) => item.key === room)?.audience}
        </span>
      </header>
      <nav
        aria-label="Các phòng hội viên"
        className="mt-6 grid gap-2 sm:grid-cols-3"
      >
        {rooms.map((item) => {
          const Icon = item.icon;
          const selected = item.key === room;
          const isLocked =
            ranks[tier] < roomRanks[item.key] &&
            !(selected && allowed) &&
            access.data?.source !== "ADMIN";
          return (
            <button
              key={item.key}
              type="button"
              aria-pressed={selected}
              disabled={send.isPending}
              onClick={() => {
                setRoom(item.key);
                setBody("");
                setEditingMessageId(null);
                setEditBody("");
                setRemovedMessageIds(new Set());
                send.reset();
                edit.reset();
                remove.reset();
              }}
              className={`flex min-h-[4.5rem] items-center gap-3 rounded-2xl border px-3 py-3 text-left transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 ${selected ? "border-amber-600/50 bg-amber-500/10 shadow-sm" : "border-[var(--theme-border)] bg-[var(--theme-surface)] hover:border-amber-700/30 hover:bg-amber-500/5"}`}
            >
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-[var(--theme-elevated)] text-amber-700">
                <Icon aria-hidden="true" className="size-5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{item.label}</span>
                <span className="mt-0.5 block text-xs text-[var(--theme-muted)]">
                  {item.audience}
                </span>
              </span>
              {isLocked ? (
                <LockKeyhole
                  aria-hidden="true"
                  className="size-4 shrink-0 text-[var(--theme-muted)]"
                />
              ) : null}
            </button>
          );
        })}
      </nav>
      <div className="mt-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)]/80 p-3 sm:p-4">
        {!user?.id ? (
          <div
            role="status"
            className="flex min-h-36 flex-col items-center justify-center text-center"
          >
            <LockKeyhole aria-hidden="true" className="size-6 text-amber-700" />
            <p className="mt-3 font-semibold">Đăng nhập để vào phòng</p>
          </div>
        ) : access.isPending ? (
          <div
            role="status"
            aria-label="Đang kiểm tra quyền vào phòng"
            className="space-y-3 py-4"
          >
            <div className="h-4 w-40 animate-pulse rounded bg-[var(--theme-elevated)]" />
            <div className="h-16 animate-pulse rounded-xl bg-[var(--theme-elevated)]" />
            <div className="h-16 w-4/5 animate-pulse rounded-xl bg-[var(--theme-elevated)]" />
          </div>
        ) : access.isError ? (
          <div
            role="alert"
            className="flex min-h-36 flex-col items-center justify-center text-center"
          >
            <p className="font-semibold">Chưa kiểm tra được quyền truy cập</p>
            <button
              className="mt-2 min-h-10 px-3 text-sm font-semibold text-amber-700 underline"
              onClick={() => void access.refetch()}
              type="button"
            >
              Thử kiểm tra lại
            </button>
          </div>
        ) : !allowed ? (
          <div
            role="status"
            className="flex min-h-36 flex-col items-center justify-center rounded-xl bg-amber-500/5 px-4 text-center"
          >
            <LockKeyhole aria-hidden="true" className="size-6 text-amber-700" />
            <h3 className="mt-3 font-semibold">
              Phòng này dành cho hạng {membershipTiers[room].name} trở lên
            </h3>
            <p className="mt-1 max-w-lg text-sm leading-6 text-[var(--theme-muted)]">
              Hạng hiện tại chưa mở phòng này. Xem các hạng hội viên và quyền
              lợi để chọn không gian phù hợp.
            </p>
            <a
              className="mt-3 inline-flex min-h-10 items-center font-semibold text-amber-700 underline"
              href="/cong-dong/hoi-vien"
            >
              Xem hạng hội viên
            </a>
          </div>
        ) : (
          <>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 px-1">
              <p className="text-sm font-semibold">Cuộc trò chuyện</p>
              <p className="text-xs text-[var(--theme-muted)]">
                {renderedMessages.length} tin đã tải · tự làm mới mỗi 10 giây
              </p>
            </div>
            <div
              aria-label="Tin nhắn trong phòng"
              aria-live="polite"
              className="max-h-[30rem] min-h-48 space-y-3 overflow-y-auto overscroll-contain rounded-xl bg-[var(--theme-elevated)] p-3 sm:p-4"
            >
              {history.hasNextPage ? (
                <div className="flex justify-center">
                  <button
                    className="min-h-10 rounded-full border border-[var(--theme-border)] px-4 text-sm font-semibold text-amber-800 hover:bg-amber-500/10 disabled:opacity-60 dark:text-amber-200"
                    disabled={history.isFetchingNextPage}
                    onClick={() => void history.fetchNextPage()}
                    type="button"
                  >
                    {history.isFetchingNextPage
                      ? "Đang tải tin cũ hơn…"
                      : "Tải tin cũ hơn"}
                  </button>
                </div>
              ) : null}
              {history.isPending ? (
                <p
                  role="status"
                  className="py-8 text-center text-sm text-[var(--theme-muted)]"
                >
                  Đang tải cuộc trò chuyện…
                </p>
              ) : history.isError ? (
                <p role="alert" className="py-8 text-center text-sm">
                  Chưa thể tải cuộc trò chuyện.{" "}
                  <button
                    className="font-semibold text-amber-700 underline"
                    onClick={() => void history.refetch()}
                    type="button"
                  >
                    Thử lại
                  </button>
                </p>
              ) : renderedMessages.length === 0 ? (
                <div className="flex min-h-40 flex-col items-center justify-center text-center">
                  <MessageCircle
                    aria-hidden="true"
                    className="size-7 text-amber-700/70"
                  />
                  <p className="mt-3 font-semibold">
                    Phòng đang chờ câu chuyện đầu tiên
                  </p>
                  <p className="mt-1 text-sm text-[var(--theme-muted)]">
                    Gửi lời chào để bắt đầu kết nối với hội viên.
                  </p>
                </div>
              ) : (
                renderedMessages.map((message) => (
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
                        showFrame={!message.isAdmin}
                      />
                      <strong>{message.displayName}</strong>
                      {message.isAdmin ? (
                        <span className="rounded-full border border-rose-700/20 bg-rose-500/5 px-2.5 py-1 text-[0.68rem] font-semibold text-rose-800 dark:text-rose-200">
                          Quản trị viên
                        </span>
                      ) : (
                        <span className="rounded-full border border-amber-700/20 bg-amber-500/5 px-2.5 py-1 text-[0.68rem] font-semibold text-amber-800 dark:text-amber-200">
                          {membershipTiers[message.tier].name}
                        </span>
                      )}
                      <time
                        className="ml-auto text-xs text-[var(--theme-muted)]"
                        dateTime={message.createdAt}
                      >
                        {new Date(message.createdAt).toLocaleTimeString(
                          "vi-VN",
                          {
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </time>
                      {message.canEdit && editingMessageId !== message.id ? (
                        <button
                          className="inline-flex min-h-9 items-center gap-1 px-2 text-xs font-semibold text-[var(--theme-muted)] underline"
                          onClick={() => {
                            edit.reset();
                            setEditingMessageId(message.id);
                            setEditBody(message.body);
                          }}
                          type="button"
                          aria-label={"Sửa tin nhắn của " + message.displayName}
                        >
                          <Pencil aria-hidden="true" className="size-3.5" />
                          Sửa
                        </button>
                      ) : null}
                      {message.canRemove ? (
                        <button
                          className="min-h-9 px-2 text-xs font-semibold text-[var(--theme-muted)] underline"
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(message.id)}
                          type="button"
                          aria-label={"Gỡ tin nhắn của " + message.displayName}
                        >
                          Gỡ
                        </button>
                      ) : null}
                    </div>
                    {editingMessageId === message.id ? (
                      <form
                        className="mt-3 space-y-2"
                        onSubmit={(event) => {
                          event.preventDefault();
                          if (editBody.trim() && !edit.isPending) {
                            edit.mutate({
                              id: message.id,
                              body: editBody.trim(),
                            });
                          }
                        }}
                      >
                        <label
                          className="sr-only"
                          htmlFor={"edit-chat-" + message.id}
                        >
                          Sửa nội dung tin nhắn
                        </label>
                        <textarea
                          id={"edit-chat-" + message.id}
                          className="min-h-20 w-full resize-y rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-2.5 text-sm leading-6 text-[var(--theme-text)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600"
                          maxLength={2000}
                          value={editBody}
                          onChange={(event) => setEditBody(event.target.value)}
                          disabled={edit.isPending}
                        />
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="text-xs text-[var(--theme-muted)]">
                            {editBody.length}/2.000 ký tự
                          </span>
                          <div className="flex gap-2">
                            <button
                              className="inline-flex min-h-9 items-center gap-1 rounded-lg px-3 text-xs font-semibold text-[var(--theme-muted)] hover:bg-[var(--theme-elevated)]"
                              onClick={() => {
                                setEditingMessageId(null);
                                setEditBody("");
                                edit.reset();
                              }}
                              type="button"
                              disabled={edit.isPending}
                            >
                              <X aria-hidden="true" className="size-3.5" />
                              Hủy
                            </button>
                            <Button
                              className="min-h-9 rounded-lg px-3 text-xs"
                              disabled={!editBody.trim() || edit.isPending}
                              type="submit"
                            >
                              {edit.isPending ? "Đang lưu…" : "Lưu sửa"}
                            </Button>
                          </div>
                        </div>
                        {edit.isError ? (
                          <p role="alert" className="text-sm text-red-700">
                            Chưa thể sửa tin nhắn. Vui lòng thử lại.
                          </p>
                        ) : null}
                      </form>
                    ) : (
                      <>
                        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-7 sm:text-base">
                          {message.body}
                        </p>
                        {message.editedAt ? (
                          <p className="mt-1 text-xs text-[var(--theme-muted)]">
                            Đã chỉnh sửa
                          </p>
                        ) : null}
                      </>
                    )}
                    {remove.isError ? (
                      <p role="alert" className="mt-2 text-sm text-red-700">
                        Chưa thể gỡ tin nhắn. Vui lòng thử lại.
                      </p>
                    ) : null}
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
              <label
                className="min-w-0 flex-1 text-xs font-semibold text-[var(--theme-muted)]"
                htmlFor="community-chat-body"
              >
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
                <span className="mt-1 block text-right font-normal">
                  {body.length}/2.000 ký tự
                </span>
              </label>
              <Button
                className="min-h-12 shrink-0 rounded-xl px-5"
                type="submit"
                disabled={!body.trim() || send.isPending}
              >
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
