"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck, ChevronRight, X } from "lucide-react";
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
  const panelRef = useRef<HTMLElement>(null);
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
    const panel = panelRef.current;
    const focusableSelector =
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const firstFocusable = panel?.querySelector<HTMLElement>(focusableSelector);
    firstFocusable?.focus();

    function closePanel() {
      setOpen(false);
      buttonRef.current?.focus();
    }
    function closeOnOutsideClick(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) closePanel();
    }
    function manageKeyboard(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closePanel();
        return;
      }
      if (event.key !== "Tab" || !panel) return;
      const focusable = Array.from(
        panel.querySelectorAll<HTMLElement>(focusableSelector),
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", manageKeyboard);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", manageKeyboard);
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
          aria-modal="true"
          className="notification-panel"
          ref={panelRef}
          role="dialog"
        >
          <header className="notification-panel__header">
            <div>
              <p>Trung tâm cập nhật</p>
              <h2>Thông báo</h2>
            </div>
            <div className="notification-panel__header-actions">
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
              <button
                aria-label="Đóng thông báo"
                className="notification-panel__close"
                onClick={() => {
                  setOpen(false);
                  buttonRef.current?.focus();
                }}
                type="button"
              >
                <X aria-hidden="true" className="size-5" />
              </button>
            </div>
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
