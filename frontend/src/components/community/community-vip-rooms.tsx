"use client";

import { useQueries } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Check,
  Crown,
  Gem,
  HeartHandshake,
  LockKeyhole,
} from "lucide-react";
import Link from "next/link";

import { membershipApi } from "@/lib/api/client";
import type { MembershipTier } from "@/lib/api/types";
import { useAuthStatus, useAuthUser } from "@/lib/auth/user-context";

const vipRooms = [
  {
    key: "COMPANION" as const,
    title: "Phòng Đồng hành",
    audience: "Vàng và Kim cương",
    accessLabel: "Vàng trở lên",
    summary: "Kết nối sâu hơn và chia sẻ cơ hội cùng cộng đồng đồng hành.",
    icon: HeartHandshake,
  },
  {
    key: "PRESTIGE" as const,
    title: "Phòng Tinh hoa",
    audience: "Kim cương",
    accessLabel: "Kim cương",
    summary: "Không gian trao đổi dành riêng cho hội viên Tinh hoa.",
    icon: Gem,
  },
];

export function CommunityVipRooms() {
  const authStatus = useAuthStatus();
  const user = useAuthUser();
  const roomAccess = useQueries({
    queries: vipRooms.map((room) => ({
      queryKey: ["membership-chat-access", user?.id, room.key],
      queryFn: () => membershipApi.chatAccess(room.key),
      enabled: authStatus === "authenticated" && Boolean(user?.id),
      staleTime: 30_000,
      retry: false,
    })),
  });

  return (
    <section
      aria-labelledby="community-member-rooms-heading"
      className="relative isolate my-5 overflow-hidden rounded-[1.75rem] border border-amber-700/20 bg-gradient-to-br from-[var(--theme-surface)] via-[var(--theme-elevated)] to-[var(--theme-surface)] p-4 shadow-sm sm:my-7 sm:p-6"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-12 -top-20 -z-10 size-64 rounded-full bg-amber-400/10 blur-3xl"
      />
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="grid size-11 shrink-0 place-items-center rounded-2xl border border-amber-700/20 bg-amber-500/10 text-amber-700 sm:size-12">
            <Crown aria-hidden="true" className="size-5 sm:size-6" />
          </span>
          <div>
            <p className="text-[0.65rem] font-bold uppercase tracking-[0.18em] text-amber-700">
              Không gian riêng theo hạng
            </p>
            <h2
              className="mt-1 text-lg font-bold tracking-tight text-[var(--theme-text)] sm:text-xl"
              id="community-member-rooms-heading"
            >
              Phòng hội viên
            </h2>
            <p className="mt-1 max-w-xl text-xs leading-5 text-[var(--theme-muted)] sm:text-sm">
              Tự mở theo hạng đang hiệu lực, không cần đăng ký phòng.
            </p>
          </div>
        </div>
        <Link
          className="inline-flex min-h-10 items-center gap-1 rounded-full border border-amber-700/20 bg-[var(--theme-surface)] px-3 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-500/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 dark:text-amber-200 sm:text-sm"
          href="/cong-dong/hoi-vien"
        >
          Xem quyền lợi <ArrowUpRight aria-hidden="true" className="size-4" />
        </Link>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {vipRooms.map((room, index) => {
          const Icon = room.icon;
          const isAuthenticated = authStatus === "authenticated";
          const access = roomAccess[index];
          const isChecking =
            authStatus === "loading" || (isAuthenticated && access?.isFetching);
          const canAccess = isAuthenticated && access?.data?.allowed === true;
          const roomHref = `/membership?room=${room.key}`;
          const actionHref = !isAuthenticated
            ? `/login?next=${encodeURIComponent(roomHref)}`
            : canAccess || access?.isError
              ? roomHref
              : "/cong-dong/hoi-vien";
          const actionLabel = isChecking
            ? "Đang kiểm tra"
            : canAccess
              ? "Mở trò chuyện"
              : isAuthenticated && access?.isError
                ? "Kiểm tra lại"
                : isAuthenticated
                  ? "Xem gói"
                  : "Đăng nhập";

          return (
            <article
              className={`flex min-w-0 items-start gap-3 rounded-2xl border bg-[var(--theme-surface)] p-4 transition-all sm:p-5 ${canAccess ? "border-amber-600/35 shadow-sm" : "border-[var(--theme-border)] hover:border-amber-700/30"}`}
              key={room.key}
            >
              <span className="grid size-12 shrink-0 place-items-center rounded-2xl border border-amber-700/15 bg-amber-500/10 text-amber-700">
                <Icon aria-hidden="true" className="size-6" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-base font-bold tracking-tight text-[var(--theme-text)] sm:text-lg">
                    {room.title}
                  </h3>
                  <span
                    className={`inline-flex min-h-7 items-center gap-1.5 rounded-full border px-2.5 text-[0.68rem] font-semibold ${canAccess ? "border-emerald-700/20 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200" : "border-amber-700/20 bg-amber-500/5 text-[var(--theme-muted)]"}`}
                  >
                    {canAccess ? (
                      <Check aria-hidden="true" className="size-3.5" />
                    ) : (
                      <LockKeyhole aria-hidden="true" className="size-3.5" />
                    )}
                    {isChecking
                      ? "Đang kiểm tra"
                      : canAccess
                        ? "Đã mở quyền"
                        : room.accessLabel}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
                  {room.summary}
                </p>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--theme-border)] pt-3">
                  <span className="text-xs text-[var(--theme-muted)]">
                    Dành cho {room.audience}
                  </span>
                  {isChecking ? (
                    <span
                      role="status"
                      className="inline-flex min-h-10 items-center px-2 text-xs font-semibold text-[var(--theme-muted)]"
                    >
                      {actionLabel}…
                    </span>
                  ) : (
                    <Link
                      className={`inline-flex min-h-10 items-center gap-2 rounded-xl px-3 text-xs font-bold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-600 ${canAccess ? "bg-amber-500 text-stone-950 hover:bg-amber-400" : "border border-[var(--theme-border)] hover:border-amber-700/30 hover:bg-amber-500/5"}`}
                      href={actionHref}
                    >
                      {actionLabel}{" "}
                      <ArrowUpRight aria-hidden="true" className="size-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
