"use client";
import "../membership/community-chat.css";

import { useQueries } from "@tanstack/react-query";
import { ArrowUpRight, Gem, HeartHandshake } from "lucide-react";
import Link from "next/link";

import { membershipApi } from "@/lib/api/client";
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
      className="member-room-entry"
    >
      <header className="member-room-entry__header">
        <div>
          <h2 id="community-member-rooms-heading" className="text-lg font-bold">
            Trò chuyện hội viên
          </h2>
          <p className="mt-1 text-sm text-[var(--theme-muted)]">
            Chọn phòng để bắt đầu kết nối.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 shrink-0 items-center text-sm font-semibold underline"
          href="/cong-dong/hoi-vien"
        >
          Quyền lợi
        </Link>
      </header>
      <div className="member-room-entry__list">
        {vipRooms.map((room, index) => {
          const Icon = room.icon;
          const access = roomAccess[index];
          const authenticated = authStatus === "authenticated";
          const checking =
            authStatus === "loading" || (authenticated && access?.isFetching);
          const allowed = authenticated && access?.data?.allowed === true;
          const href = `/membership?room=${room.key}#community-chat`;
          return (
            <article className="member-room-entry__room" key={room.key}>
              <Icon
                aria-hidden="true"
                className="size-6 shrink-0 text-[var(--theme-accent)]"
              />
              <div>
                <h3 className="font-bold">{room.title}</h3>
                <p className="mt-1 text-sm text-[var(--theme-muted)]">
                  {checking
                    ? "Đang kiểm tra quyền…"
                    : access?.isError
                      ? "Chưa xác nhận được quyền vào phòng"
                      : allowed
                        ? "Bạn có thể tham gia"
                        : room.accessLabel}
                </p>
              </div>
              {checking ? (
                <span
                  role="status"
                  className="text-sm text-[var(--theme-muted)]"
                >
                  Đang tải…
                </span>
              ) : (
                <Link
                  href={
                    !authenticated
                      ? `/login?next=${encodeURIComponent(href)}`
                      : allowed || access?.isError
                        ? href
                        : "/cong-dong/hoi-vien"
                  }
                >
                  {!authenticated
                    ? "Đăng nhập"
                    : allowed || access?.isError
                      ? "Vào phòng"
                      : "Xem gói"}
                  <ArrowUpRight aria-hidden="true" className="size-4" />
                </Link>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
