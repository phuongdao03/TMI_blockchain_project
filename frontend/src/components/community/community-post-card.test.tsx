import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityPostCard } from "@/components/community/community-post-card";

const api = vi.hoisted(() => ({ likePost: vi.fn(), unlikePost: vi.fn(), bookmarkPost: vi.fn(), unbookmarkPost: vi.fn() }));
const auth = vi.hoisted(() => ({ user: null as null | { id: string } }));
vi.mock("@/lib/api/client", () => ({ communityApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

const post = {
  id: "post-1", slug: "chuyen-lang", title: "Chuyện làng", excerpt: "Một câu chuyện.",
  category: { id: "cat-1", name: "Di sản", slug: "di-san" },
  author: { id: "member-1", username: "lan-anh", displayName: "Lan Anh", avatarUrl: null },
  publishedAt: "2026-10-14T10:00:00Z", likeCount: 2, commentCount: 4, viewCount: 15,
  viewerHasLiked: false, viewerHasBookmarked: false, tags: [], relatedWork: null, images: [],
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: "viewer-1" };
  api.likePost.mockResolvedValue({ postId: "post-1", likeCount: 3, isLiked: true });
  api.unlikePost.mockResolvedValue({ postId: "post-1", likeCount: 2, isLiked: false });
  api.bookmarkPost.mockResolvedValue({ postId: "post-1", isBookmarked: true });
  api.unbookmarkPost.mockResolvedValue({ postId: "post-1", isBookmarked: false });
});

describe("CommunityPostCard", () => {
  it("shows the author profile link and engagement counts with quick actions", async () => {
    const user = userEvent.setup();
    render(<CommunityPostCard post={post} />, { wrapper });

    expect(screen.getByRole("link", { name: "Lan Anh" }).getAttribute("href")).toBe("/community/members/lan-anh");
    expect(screen.getByText("15 lượt xem")).toBeDefined();
    expect(screen.getByText("4 bình luận")).toBeDefined();
    expect(screen.getByRole("button", { name: "Chia sẻ bài viết" })).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Thích bài viết (2)" }));
    expect(api.likePost).toHaveBeenCalledWith("post-1");
    expect(await screen.findByRole("button", { name: "Bỏ thích bài viết (3)" })).toBeDefined();
  });

  it("keeps interaction actions behind sign-in when the viewer is anonymous", () => {
    auth.user = null;
    render(<CommunityPostCard post={post} />, { wrapper });

    expect(screen.queryByRole("button", { name: /thích bài viết/i })).toBeNull();
    expect(screen.getByRole("link", { name: "Đăng nhập để tương tác" })).toBeDefined();
  });
});
