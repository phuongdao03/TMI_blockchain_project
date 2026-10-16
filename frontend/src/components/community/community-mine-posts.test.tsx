import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityMinePosts } from "@/components/community/community-mine-posts";

const api = vi.hoisted(() => ({ myPosts: vi.fn(), deletePost: vi.fn() }));
const auth = vi.hoisted(() => ({ user: { id: "member-1" } }));
vi.mock("@/lib/api/client", () => ({
  communityMemberApi: api,
  communityApi: api,
}));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const post = (
  id: string,
  status: "DRAFT" | "PENDING" | "REJECTED" | "PUBLISHED" | "HIDDEN",
) => ({
  id,
  slug: `slug-${id}`,
  title: `Bài ${status}`,
  content: "Nội dung bài.",
  status,
  moderationReason: status === "REJECTED" ? "Bổ sung nguồn" : null,
  category: { id: "cat-1", name: "Di sản", slug: "di-san" },
  tags: [],
  relatedWork: null,
  images: [],
  createdAt: "2026-10-13T09:00:00Z",
  updatedAt: "2026-10-14T09:00:00Z",
});

beforeEach(() => {
  vi.clearAllMocks();
  api.myPosts.mockResolvedValue({
    data: [
      post("draft-1", "DRAFT"),
      post("pending-1", "PENDING"),
      post("rejected-1", "REJECTED"),
      post("published-1", "PUBLISHED"),
      post("hidden-1", "HIDDEN"),
    ],
    meta: { requestId: "owner-posts", page: 1, pageSize: 20, total: 5 },
  });
  api.deletePost.mockResolvedValue(undefined);
});

describe("CommunityMinePosts", () => {
  it("shows status filters and lets owners continue editing published or removed posts", async () => {
    render(<CommunityMinePosts page={1} />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Bài DRAFT" }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục chỉnh sửa: Bài DRAFT" })
        .getAttribute("href"),
    ).toBe("/community/new?postId=draft-1");
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục chỉnh sửa: Bài REJECTED" })
        .getAttribute("href"),
    ).toBe("/community/new?postId=rejected-1");
    expect(screen.getByText("Bổ sung nguồn")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Xem bài đã đăng: Bài PUBLISHED" })
        .getAttribute("href"),
    ).toBe("/community/posts/slug-published-1");
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục chỉnh sửa: Bài PUBLISHED" })
        .getAttribute("href"),
    ).toBe("/community/new?postId=published-1");
    expect(screen.getByText("Đã gỡ bởi quản trị viên")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục chỉnh sửa: Bài HIDDEN" })
        .getAttribute("href"),
    ).toBe("/community/new?postId=hidden-1");
    expect(
      screen.getAllByText("Chờ xử lý (bài viết cũ)").length,
    ).toBeGreaterThan(1);
    expect(
      screen.getByRole("link", { name: "Bản nháp" }).getAttribute("href"),
    ).toBe("/community/mine?status=DRAFT&page=1");
  });

  it("asks for confirmation before soft-deleting an owned post", async () => {
    const user = userEvent.setup();
    render(<CommunityMinePosts page={1} />, { wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Xóa bài: Bài DRAFT" }),
    );
    expect(
      screen.getByRole("button", { name: "Xác nhận xóa: Bài DRAFT" }),
    ).toBeDefined();
    await user.click(
      screen.getByRole("button", { name: "Xác nhận xóa: Bài DRAFT" }),
    );
    expect(api.deletePost).toHaveBeenCalledWith("draft-1");
  });
});
