import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NotificationCenter } from "./notification-center";

const api = vi.hoisted(() => ({
  notification: {
    list: vi.fn(),
    markAllRead: vi.fn(),
    markRead: vi.fn(),
    unreadCount: vi.fn(),
  },
  invitation: {
    accept: vi.fn(),
    decline: vi.fn(),
  },
}));

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  notificationApi: api.notification,
  staffInvitationsApi: api.invitation,
}));

function renderCenter() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <NotificationCenter />
    </QueryClientProvider>,
  );
}

describe("NotificationCenter reviewer invitation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.notification.unreadCount.mockResolvedValue({ unreadCount: 1 });
    api.notification.list.mockResolvedValue({
      data: [
        {
          id: "notification-1",
          type: "staff.reviewer_invited",
          title: "Lời mời trở thành Người kiểm duyệt",
          body: "Quản trị viên mời bạn tham gia thẩm định hồ sơ.",
          data: { invitationId: "invitation-1", actionPath: "/notifications" },
          readAt: null,
          createdAt: "2026-09-06T00:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 12, total: 1 },
    });
    api.invitation.accept.mockResolvedValue({ status: "ACCEPTED" });
  });

  it("lets the invited account accept its reviewer role", async () => {
    const user = userEvent.setup();
    renderCenter();

    await user.click(
      await screen.findByRole("button", {
        name: "Chấp nhận và trở thành Người kiểm duyệt",
      }),
    );

    await waitFor(() =>
      expect(api.invitation.accept).toHaveBeenCalledWith("invitation-1"),
    );
  });
});
