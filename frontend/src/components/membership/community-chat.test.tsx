import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  messages: vi.fn(),
  chatAccess: vi.fn(),
  send: vi.fn(),
  removeMessage: vi.fn(),
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
    api.messages.mockResolvedValue([]);
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
        client={new QueryClient({
          defaultOptions: { queries: { retry: false } },
        })}
      >
        <CommunityChat tier="SILVER" />
      </QueryClientProvider>,
    );

    const roomGroup = screen.getByRole("navigation", {
      name: "Các phòng hội viên",
    });
    expect(within(roomGroup).getAllByRole("button")).toHaveLength(3);
    await screen.findByText(/Phòng đang chờ câu chuyện đầu tiên/i);
    expect(api.messages).toHaveBeenCalledWith("MEMBER");

    fireEvent.click(within(roomGroup).getByRole("button", { name: /Đồng hành/ }));
    expect(
      await screen.findByText(/Phòng này dành cho hạng Vàng trở lên/i),
    ).toBeDefined();
    expect(api.messages).not.toHaveBeenCalledWith("COMPANION");
  });
});
