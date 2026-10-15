import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityPostDetail } from "@/components/community/community-post-detail";

const api = vi.hoisted(() => ({
  post: vi.fn(),
  comments: vi.fn(),
  createComment: vi.fn(),
  likePost: vi.fn(),
  unlikePost: vi.fn(),
  bookmarkPost: vi.fn(),
  unbookmarkPost: vi.fn(),
  recordPostView: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ communityApi: api }));
const auth = vi.hoisted(() => ({ user: { id: "viewer-detail" } }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("CommunityPostDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.user = { id: "viewer-detail" };
    api.post.mockResolvedValue({
      id: "post-1",
      slug: "chuyen-di-lang-co",
      title: "Ký ức về ngôi làng",
      excerpt: "Một câu chuyện.",
      content: "Ngày ấy <script>alert(1)</script>\nchúng tôi trở về làng.",
      category: {
        id: "cat-1",
        name: "Di sản và văn hóa",
        slug: "heritage-culture",
      },
      author: { displayName: null },
      publishedAt: "2026-10-13T09:00:00Z",
      likeCount: 2,
      commentCount: 0,
      viewCount: 17,
      viewerHasLiked: false,
      viewerHasBookmarked: false,
      relatedWork: {
        id: "work-2",
        title: "Nghệ thuật khảm trai",
        slug: "nghe-thuat-kham-trai",
      },
      images: [
        {
          id: "detail-image",
          url: "/api/v1/community/posts/chuyen-di-lang-co/media/detail-image",
        },
      ],
    });
    api.comments.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "comments-empty", page: 1, pageSize: 20, total: 0 },
    });
    api.recordPostView.mockResolvedValue(undefined);
  });

  it("shows published content as text and uses the safe author fallback", async () => {
    render(<CommunityPostDetail slug="chuyen-di-lang-co" />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Ký ức về ngôi làng" }),
    ).toBeDefined();
    expect(
      screen.getByText(
        (_, element) =>
          element?.tagName === "P" &&
          Boolean(element.textContent?.includes("<script>alert(1)</script>")),
      ),
    ).toBeDefined();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("Thành viên cộng đồng")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Tác phẩm liên quan: Nghệ thuật khảm trai" })
        .getAttribute("href"),
    ).toBe("/works/nghe-thuat-kham-trai");
    const image = screen.getByRole("img", {
      name: "Ký ức về ngôi làng — ảnh đính kèm 1",
    });
    expect(image.getAttribute("src")).toBe(
      "/api/v1/community/posts/chuyen-di-lang-co/media/detail-image",
    );
    expect(
      await screen.findByRole("heading", { name: "Thảo luận" }),
    ).toBeDefined();
    expect(api.post).toHaveBeenCalledWith(
      "chuyen-di-lang-co",
      expect.any(AbortSignal),
    );
    await waitFor(() =>
      expect(api.recordPostView).toHaveBeenCalledWith("post-1"),
    );
    expect(screen.getByText("17 lượt xem")).toBeDefined();
  });

  it("does not reveal whether an unavailable slug is a draft or rejected post", async () => {
    api.post.mockRejectedValueOnce(
      Object.assign(new Error("not found"), { status: 404 }),
    );
    render(<CommunityPostDetail slug="private-draft" />, { wrapper });

    expect(
      await screen.findByRole("heading", { name: "Không tìm thấy bài viết" }),
    ).toBeDefined();
    expect(screen.queryByText(/bản nháp|bị từ chối/i)).toBeNull();
  });

  it("scopes personalized post details to the current viewer", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(<CommunityPostDetail slug="chuyen-di-lang-co" />, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      ),
    });

    await screen.findByRole("heading", { name: "Ký ức về ngôi làng" });
    expect(
      client
        .getQueryCache()
        .getAll()
        .some((query) => query.queryKey.includes("viewer-detail")),
    ).toBe(true);
  });
});
