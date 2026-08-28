"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  Inbox,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { notificationApi } from "@/lib/api/client";
import type { NotificationItem } from "@/lib/api/types";

import {
  formatNotificationTime,
  presentNotification,
} from "./notification-presentation";

const PAGE_SIZE = 12;

export function NotificationCenter() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const notifications = useQuery({
    queryKey: ["notifications", "list", page, unreadOnly],
    queryFn: () => notificationApi.list(page, PAGE_SIZE, unreadOnly),
  });
  const unread = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: notificationApi.unreadCount,
  });
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };
  const markRead = useMutation({
    mutationFn: notificationApi.markRead,
    onSuccess: refresh,
  });
  const markAllRead = useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: refresh,
  });
  const total = notifications.data?.meta.total ?? 0;
  const lastPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function selectFilter(nextUnreadOnly: boolean) {
    setUnreadOnly(nextUnreadOnly);
    setPage(1);
  }

  function openItem(item: NotificationItem) {
    if (!item.readAt) markRead.mutate(item.id);
  }

  return (
    <div className="notification-center">
      <header className="notification-center__hero">
        <div>
          <p className="notification-center__eyebrow">
            <Bell aria-hidden="true" className="size-4" />
            Trung tâm cập nhật
          </p>
          <h1>Thông báo của bạn</h1>
          <p>
            Theo dõi hồ sơ, công việc thẩm định và các tác vụ cần xử lý trong
            một luồng thống nhất.
          </p>
        </div>
        <div
          className="notification-center__summary"
          aria-label="Tóm tắt thông báo"
        >
          <strong>{unread.data?.unreadCount ?? 0}</strong>
          <span>chưa đọc</span>
        </div>
      </header>

      <section className="notification-center__workspace">
        <div className="notification-center__toolbar">
          <div
            aria-label="Lọc thông báo"
            className="notification-center__filters"
          >
            <button
              aria-pressed={!unreadOnly}
              className={!unreadOnly ? "is-active" : ""}
              onClick={() => selectFilter(false)}
              type="button"
            >
              Tất cả
            </button>
            <button
              aria-pressed={unreadOnly}
              className={unreadOnly ? "is-active" : ""}
              onClick={() => selectFilter(true)}
              type="button"
            >
              Chưa đọc
              {(unread.data?.unreadCount ?? 0) > 0 ? (
                <span>{unread.data?.unreadCount}</span>
              ) : null}
            </button>
          </div>
          {(unread.data?.unreadCount ?? 0) > 0 ? (
            <button
              className="notification-center__read-all"
              disabled={markAllRead.isPending}
              onClick={() => markAllRead.mutate()}
              type="button"
            >
              <CheckCheck aria-hidden="true" className="size-4" />
              Đánh dấu tất cả đã đọc
            </button>
          ) : null}
        </div>

        {notifications.isPending ? (
          <p className="notification-center__state" role="status">
            Đang tải thông báo…
          </p>
        ) : null}
        {notifications.isError ? (
          <div className="notification-center__state" role="alert">
            <Inbox aria-hidden="true" />
            <h2>Chưa thể tải thông báo</h2>
            <p>Vui lòng kiểm tra kết nối và thử lại.</p>
            <button onClick={() => notifications.refetch()} type="button">
              Thử lại
            </button>
          </div>
        ) : null}
        {notifications.data?.data.length === 0 ? (
          <div className="notification-center__state">
            <Bell aria-hidden="true" />
            <h2>
              {unreadOnly ? "Bạn đã đọc hết thông báo" : "Chưa có thông báo"}
            </h2>
            <p>
              {unreadOnly
                ? "Các cập nhật mới cần chú ý sẽ xuất hiện tại đây."
                : "Khi hồ sơ hoặc công việc thay đổi, bạn sẽ nhận được cập nhật tại đây."}
            </p>
          </div>
        ) : null}

        <div className="notification-center__list">
          {notifications.data?.data.map((item) => {
            const presentation = presentNotification(item);
            const inner = (
              <>
                <span
                  aria-hidden="true"
                  className={`notification-center__indicator notification-center__indicator--${presentation.tone}`}
                />
                <span className="notification-center__content">
                  <span className="notification-center__meta">
                    {presentation.groupLabel} ·{" "}
                    {formatNotificationTime(item.createdAt)}
                  </span>
                  <strong>{item.title}</strong>
                  <span>{item.body}</span>
                </span>
                <span className="notification-center__action">
                  {presentation.actionLabel}
                  <ChevronRight aria-hidden="true" className="size-4" />
                </span>
              </>
            );
            const className = `notification-center__item${item.readAt ? "" : " is-unread"}`;
            return presentation.actionPath ? (
              <Link
                className={className}
                href={presentation.actionPath}
                key={item.id}
                onClick={() => openItem(item)}
              >
                {inner}
              </Link>
            ) : (
              <button
                className={className}
                key={item.id}
                onClick={() => openItem(item)}
                type="button"
              >
                {inner}
              </button>
            );
          })}
        </div>

        {total > PAGE_SIZE ? (
          <nav
            aria-label="Phân trang thông báo"
            className="notification-center__pagination"
          >
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              type="button"
            >
              <ChevronLeft aria-hidden="true" className="size-4" />
              Trước
            </button>
            <span>
              Trang {page} / {lastPage}
            </span>
            <button
              disabled={page >= lastPage}
              onClick={() => setPage(page + 1)}
              type="button"
            >
              Sau
              <ChevronRight aria-hidden="true" className="size-4" />
            </button>
          </nav>
        ) : null}
      </section>
    </div>
  );
}
