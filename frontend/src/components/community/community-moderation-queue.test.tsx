import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityModerationQueue } from "@/components/community/community-moderation-queue";

const api = vi.hoisted(() => ({
  pendingPosts: vi.fn(),
  publishPost: vi.fn(),
  rejectPost: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ communityAdminApi: api }));

const pendingPost = {
  id: "post-1",
  slug: "y-tuong-lang-nghe",
  title: "Ý tưởng về làng nghề",
  content: "Một đề xuất cần được xem xét.",
  status: "PENDING" as const,
  category: {
    id: "cat-1",
    name: "Cộng đồng và con người",
    slug: "people-community",
  },
  author: { displayName: "Nguyễn Minh An" },
  submittedAt: "2026-10-13T09:00:00Z",
  createdAt: "2026-10-13T08:00:00Z",
  updatedAt: "2026-10-13T08:30:00Z",
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  api.pendingPosts.mockResolvedValue({
    success: true,
    data: [pendingPost],
    meta: { requestId: "pending-1", page: 1, pageSize: 20, total: 1 },
  });
  api.publishPost.mockResolvedValue({ id: "post-1", status: "PUBLISHED" });
  api.rejectPost.mockResolvedValue({ id: "post-1", status: "REJECTED" });
});

describe("CommunityModerationQueue", () => {
  it("requires a reason before publishing and refreshes the pending queue", async () => {
    const user = userEvent.setup();
    render(<CommunityModerationQueue />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Ý tưởng về làng nghề" }),
    ).toBeDefined();
    expect(screen.getByText("Nguyễn Minh An")).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Duyệt và đăng bài" }).hasAttribute(
        "disabled",
      ),
    ).toBe(true);

    await user.type(
      screen.getByLabelText(/Lý do kiểm duyệt/),
      "Nội dung phù hợp với tiêu chí cộng đồng.",
    );
    await user.click(screen.getByRole("button", { name: "Duyệt và đăng bài" }));

    await waitFor(() =>
      expect(api.publishPost).toHaveBeenCalledWith("post-1", {
        reason: "Nội dung phù hợp với tiêu chí cộng đồng.",
      }),
    );
    expect(api.pendingPosts.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("rejects a post only after a moderator enters a reason", async () => {
    const user = userEvent.setup();
    render(<CommunityModerationQueue />, { wrapper });
    await screen.findByRole("heading", { name: "Ý tưởng về làng nghề" });

    await user.type(
      screen.getByLabelText(/Lý do kiểm duyệt/),
      "Thiếu nguồn tham khảo.",
    );
    await user.click(screen.getByRole("button", { name: "Từ chối bài viết" }));

    await waitFor(() =>
      expect(api.rejectPost).toHaveBeenCalledWith("post-1", {
        reason: "Thiếu nguồn tham khảo.",
      }),
    );
  });

  it("paginates the pending queue using server totals", async () => {
    const user = userEvent.setup();
    api.pendingPosts.mockImplementation((page: number) =>
      Promise.resolve({
        success: true,
        data: [pendingPost],
        meta: { requestId: `queue-${page}`, page, pageSize: 20, total: 21 },
      }),
    );
    render(<CommunityModerationQueue />, { wrapper });

    await screen.findByRole("heading", { name: "Ý tưởng về làng nghề" });
    await user.click(screen.getByRole("button", { name: "Trang sau" }));
    await waitFor(() =>
      expect(api.pendingPosts).toHaveBeenLastCalledWith(
        2,
        expect.any(AbortSignal),
      ),
    );
    expect(await screen.findByText("Trang 2 / 2")).toBeDefined();
  });
});
