import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  messages: vi.fn(),
  chatAccess: vi.fn(),
  send: vi.fn(),
  removeMessage: vi.fn(),
  editMessage: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  membershipApi: api,
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "member-1" }),
}));

import { CommunityChat } from "./community-chat";

describe("community chat tier access", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.messages.mockResolvedValue({
      items: [],
      hasMore: false,
      nextCursor: null,
    });
    api.send.mockResolvedValue({});
    api.editMessage.mockImplementation((id: string, body: string) =>
      Promise.resolve({ id, body, editedAt: "2026-10-26T10:00:00Z" }),
    );
    api.removeMessage.mockResolvedValue({ status: "removed" });
    api.chatAccess.mockImplementation((room: string) =>
      Promise.resolve({
        room,
        allowed: room === "MEMBER",
        source: room === "MEMBER" ? "TIER" : "NONE",
      }),
    );
  });

  it("lets Silver use the Member room without adding a Silver room", async () => {
    render(
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false } },
          })
        }
      >
        <CommunityChat tier="SILVER" />
      </QueryClientProvider>,
    );

    const roomGroup = screen.getByRole("navigation", {
      name: "Các phòng hội viên",
    });
    expect(within(roomGroup).getAllByRole("button")).toHaveLength(3);
    await screen.findByText(/Phòng đang chờ câu chuyện đầu tiên/i);
    expect(api.messages).toHaveBeenCalledWith("MEMBER", {
      cursor: null,
      limit: 50,
    });

    fireEvent.click(
      within(roomGroup).getByRole("button", { name: /Đồng hành/ }),
    );
    expect(
      await screen.findByText(/Phòng này dành cho hạng Vàng trở lên/i),
    ).toBeDefined();
    expect(
      api.messages.mock.calls.some(
        ([requestedRoom]) => requestedRoom === "COMPANION",
      ),
    ).toBe(false);
  });

  it("keeps loaded history while polling and supports owner edits and removes", async () => {
    const newest = {
      id: "new-message",
      displayName: "Member",
      avatarUrl: null,
      body: "Latest message",
      tier: "SILVER",
      createdAt: "2026-10-26T10:02:00Z",
      editedAt: null,
      isAdmin: false,
      canEdit: true,
      canRemove: true,
    };
    const older = {
      ...newest,
      id: "older-message",
      body: "Older history",
      createdAt: "2026-10-26T09:00:00Z",
      canEdit: false,
      canRemove: false,
    };
    const admin = {
      ...newest,
      id: "admin-message",
      displayName: "Quản trị viên THV",
      body: "Admin announcement",
      isAdmin: true,
      canEdit: false,
      canRemove: false,
    };
    api.editMessage.mockResolvedValue({
      ...newest,
      body: "Edited message",
      editedAt: "2026-10-26T10:04:00Z",
    });
    api.messages.mockImplementation(
      (_room: string, options?: { cursor?: string | null }) =>
        Promise.resolve(
          options?.cursor
            ? { items: [older], hasMore: false, nextCursor: null }
            : {
                items: [newest, admin],
                hasMore: true,
                nextCursor: "cursor-older",
              },
        ),
    );
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <CommunityChat tier="SILVER" />
      </QueryClientProvider>,
    );

    await screen.findByText("Latest message");
    const newestArticle = screen
      .getByText("Latest message")
      .closest<HTMLElement>("article");
    if (!newestArticle) throw new Error("Expected newest chat message article");
    const adminArticle = screen
      .getByText("Admin announcement")
      .closest<HTMLElement>("article");
    if (!adminArticle) throw new Error("Expected admin chat message article");
    expect(within(adminArticle).getByText("Quản trị viên")).toBeDefined();
    expect(within(adminArticle).queryByText("Kim cương")).toBeNull();
    expect(
      adminArticle?.querySelector(
        'img[src*="/assets/membership/avatar-frames/"]',
      ),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Tải tin cũ hơn" }));
    await screen.findByText("Older history");

    queryClient.setQueryData(
      ["membership-chat-history", "member-1", "MEMBER", "latest"],
      {
        items: [
          {
            ...newest,
            id: "polled-message",
            body: "Newly polled message",
            createdAt: "2026-10-26T10:03:00Z",
          },
        ],
        hasMore: true,
        nextCursor: "latest-cursor",
      },
    );
    await screen.findByText("Newly polled message");
    expect(screen.getByText("Older history")).toBeDefined();

    fireEvent.click(
      within(newestArticle).getByRole("button", {
        name: "Sửa tin nhắn của Member",
      }),
    );
    fireEvent.change(screen.getByLabelText("Sửa nội dung tin nhắn"), {
      target: { value: "Edited message" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu sửa" }));
    await screen.findByText("Edited message");
    expect(api.editMessage).toHaveBeenCalledWith(
      "new-message",
      "Edited message",
    );
    expect(screen.getByText("Đã chỉnh sửa")).toBeDefined();

    fireEvent.click(
      within(newestArticle).getByRole("button", {
        name: "Gỡ tin nhắn của Member",
      }),
    );
    await screen.findByText("Older history");
    expect(screen.queryByText("Edited message")).toBeNull();
  });
});
