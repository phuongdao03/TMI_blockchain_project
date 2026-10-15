import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunitySavedPosts } from "@/components/community/community-saved-posts";

const api = vi.hoisted(() => ({
  bookmarks: vi.fn(),
  unbookmarkPost: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { id: "viewer-1" } }));

vi.mock("@/lib/api/client", () => ({
  communityApi: { unbookmarkPost: api.unbookmarkPost },
  communityMemberApi: { bookmarks: api.bookmarks },
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));

const savedPost = {
  id: "post-1",
  slug: "ky-uc-lang-co",
  title: "Ký ức làng cổ",
  excerpt: "Một câu chuyện.",
  category: { id: "cat-1", name: "Di sản", slug: "heritage-culture" },
  author: { displayName: "Lan Anh" },
  publishedAt: "2026-10-13T09:00:00Z",
  likeCount: 3,
  commentCount: 2,
  viewerHasLiked: false,
  viewerHasBookmarked: true,
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: "viewer-1" };
  api.bookmarks.mockResolvedValue({
    success: true,
    data: [savedPost],
    meta: { requestId: "bookmarks-1", page: 1, pageSize: 20, total: 22 },
  });
  api.unbookmarkPost.mockResolvedValue({
    postId: "post-1",
    isBookmarked: false,
  });
});

describe("CommunitySavedPosts", () => {
  it("lists saved published posts, removes bookmarks, and paginates", async () => {
    const user = userEvent.setup();
    render(<CommunitySavedPosts page={1} />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Bài đã lưu" }),
    ).toBeDefined();
    expect(
      await screen.findByRole("heading", { name: "Ký ức làng cổ" }),
    ).toBeDefined();
    expect(api.bookmarks).toHaveBeenCalledWith(1, expect.any(AbortSignal));

    await user.click(
      screen.getByRole("button", { name: "Bỏ lưu bài viết: Ký ức làng cổ" }),
    );
    await waitFor(() =>
      expect(api.unbookmarkPost).toHaveBeenCalledWith("post-1"),
    );
    expect(await screen.findByText("Bài viết đã được bỏ lưu.")).toBeDefined();

    const nextPage = await screen.findByRole("link", { name: "Trang sau" });
    expect(nextPage.getAttribute("href")).toBe("/community/saved?page=2");
  });

  it("provides an empty state when the member has no saved posts", async () => {
    api.bookmarks.mockResolvedValueOnce({
      success: true,
      data: [],
      meta: { requestId: "bookmarks-empty", page: 1, pageSize: 20, total: 0 },
    });
    render(<CommunitySavedPosts page={1} />, { wrapper });

    expect(await screen.findByText("Bạn chưa lưu bài viết nào.")).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Khám phá bài viết" }),
    ).toBeDefined();
  });
});
