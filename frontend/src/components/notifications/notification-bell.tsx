"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, ChevronRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { notificationApi } from "@/lib/api/client";
import type { NotificationItem } from "@/lib/api/types";

import {
  formatNotificationTime,
  presentNotification,
} from "./notification-presentation";

function NotificationRow({
  item,
  onOpen,
}: {
  item: NotificationItem;
  onOpen: (item: NotificationItem) => void;
}) {
  const presentation = presentNotification(item);
  const content = (
    <>
      <span
        aria-hidden="true"
        className={`notification-panel__status notification-panel__status--${presentation.tone}`}
      />
      <span className="min-w-0 flex-1">
        <span className="notification-panel__meta">
          {presentation.groupLabel} · {formatNotificationTime(item.createdAt)}
        </span>
        <strong className="notification-panel__title">{item.title}</strong>
        <span className="notification-panel__body">{item.body}</span>
      </span>
      <ChevronRight
        aria-hidden="true"
        className="size-4 shrink-0"
        focusable="false"
        strokeWidth={1.75}
      />
    </>
  );

  return presentation.actionPath ? (
    <Link
      className={`notification-panel__item${item.readAt ? "" : " is-unread"}`}
      href={presentation.actionPath}
      onClick={() => onOpen(item)}
    >
      {content}
    </Link>
  ) : (
    <button
      className={`notification-panel__item${item.readAt ? "" : " is-unread"}`}
      onClick={() => onOpen(item)}
      type="button"
    >
      {content}
    </button>
  );
}

export function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const unread = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: notificationApi.unreadCount,
    refetchInterval: 45_000,
    refetchOnWindowFocus: true,
  });
  const recent = useQuery({
    queryKey: ["notifications", "recent"],
    queryFn: () => notificationApi.list(1, 5),
    enabled: open,
  });
  const markRead = useMutation({
    mutationFn: notificationApi.markRead,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
  const markAllRead = useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  useEffect(() => {
    if (!open) return;
    function closeOnOutsideClick(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const unreadCount = unread.data?.unreadCount ?? 0;
  function openItem(item: NotificationItem) {
    if (!item.readAt) markRead.mutate(item.id);
    setOpen(false);
  }

  return (
    <div className="notification-bell" ref={rootRef}>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={
          unreadCount > 0
            ? `${unreadCount} thông báo chưa đọc`
            : "Mở trung tâm thông báo"
        }
        className="notification-bell__trigger"
        onClick={() => setOpen((value) => !value)}
        ref={buttonRef}
        type="button"
      >
        <Bell
          aria-hidden="true"
          className="size-5"
          focusable="false"
          strokeWidth={1.75}
        />
        {unreadCount > 0 ? (
          <span className="notification-bell__badge">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <section
          aria-label="Thông báo gần đây"
          className="notification-panel"
          role="dialog"
        >
          <header className="notification-panel__header">
            <div>
              <p>Trung tâm cập nhật</p>
              <h2>Thông báo</h2>
            </div>
            {unreadCount > 0 ? (
              <button
                disabled={markAllRead.isPending}
                onClick={() => markAllRead.mutate()}
                type="button"
              >
                <CheckCheck
                  aria-hidden="true"
                  className="size-4"
                  focusable="false"
                  strokeWidth={1.75}
                />
                Đọc tất cả
              </button>
            ) : null}
          </header>
          <div className="notification-panel__list">
            {recent.isPending ? (
              <p className="notification-panel__state" role="status">
                Đang tải thông báo…
              </p>
            ) : null}
            {recent.isError ? (
              <p className="notification-panel__state" role="alert">
                Chưa thể tải thông báo. Vui lòng thử lại.
              </p>
            ) : null}
            {recent.data?.data.length === 0 ? (
              <p className="notification-panel__state">
                Chưa có cập nhật mới cho tài khoản này.
              </p>
            ) : null}
            {recent.data?.data.map((item) => (
              <NotificationRow item={item} key={item.id} onOpen={openItem} />
            ))}
          </div>
          <Link
            className="notification-panel__footer"
            href="/notifications"
            onClick={() => setOpen(false)}
          >
            Xem tất cả thông báo
            <ChevronRight
              aria-hidden="true"
              className="size-4"
              focusable="false"
              strokeWidth={1.75}
            />
          </Link>
        </section>
      ) : null}
    </div>
  );
}
