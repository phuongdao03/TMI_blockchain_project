import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NotificationBell } from "./notification-bell";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  markAllRead: vi.fn(),
  markRead: vi.fn(),
  unreadCount: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ notificationApi: api }));

function renderBell() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <NotificationBell />
    </QueryClientProvider>,
  );
}

describe("NotificationBell", () => {
  it("shows the unread badge and marks an opened notification as read", async () => {
    api.unreadCount.mockResolvedValue({ unreadCount: 3 });
    api.list.mockResolvedValue({
      data: [
        {
          body: "Bạn có một hồ sơ thẩm định mới.",
          createdAt: "2026-08-27T10:00:00Z",
          data: {},
          id: "notification-1",
          readAt: null,
          title: "Phân công thẩm định",
          type: "review.assignment_created",
        },
      ],
      meta: { page: 1, pageSize: 5, requestId: "request-1", total: 1 },
    });
    api.markRead.mockResolvedValue({ readAt: "2026-08-27T10:01:00Z" });

    renderBell();

    const trigger = await screen.findByRole("button", {
      name: "3 thông báo chưa đọc",
    });
    fireEvent.click(trigger);
    fireEvent.click(await screen.findByText("Phân công thẩm định"));

    await waitFor(() => {
      expect(api.markRead.mock.calls[0]?.[0]).toBe("notification-1");
    });
  });

  it("marks every unread notification from the panel", async () => {
    api.unreadCount.mockResolvedValue({ unreadCount: 2 });
    api.list.mockResolvedValue({ data: [], meta: { page: 1, pageSize: 5, total: 0 } });
    api.markAllRead.mockResolvedValue({ updatedCount: 2 });

    renderBell();
    fireEvent.click(await screen.findByRole("button", { name: "2 thông báo chưa đọc" }));
    fireEvent.click(screen.getByRole("button", { name: /Đọc tất cả/i }));

    await waitFor(() => expect(api.markAllRead).toHaveBeenCalledOnce());
  });
});
