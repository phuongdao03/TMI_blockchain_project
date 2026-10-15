import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityFeed } from "@/components/community/community-feed";

const api = vi.hoisted(() => ({
  categories: vi.fn(),
  posts: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ communityApi: api }));
const auth = vi.hoisted(() => ({ user: { id: "viewer-7" } }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));

let queryClient: QueryClient;

const categories = [
  {
    id: "cat-1",
    name: "Di sản và văn hóa",
    slug: "heritage-culture",
    description: null,
    icon: null,
    sortOrder: 1,
  },
  {
    id: "cat-2",
    name: "Trải nghiệm sẻ chia",
    slug: "sharing-experiences",
    description: null,
    icon: null,
    sortOrder: 2,
  },
];

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  vi.clearAllMocks();
  auth.user = { id: "viewer-7" };
  api.categories.mockResolvedValue(categories);
  api.posts.mockResolvedValue({
    success: true,
    data: [
      {
        id: "post-1",
        slug: "chuyen-di-lang-co",
        title: "Chuyện đi làng cổ <img src=x onerror=alert(1)>",
        excerpt: "Một câu chuyện được chia sẻ.",
        category: {
          id: "cat-1",
          name: "Di sản và văn hóa",
          slug: "heritage-culture",
        },
        author: { displayName: null },
        publishedAt: "2026-10-13T09:00:00Z",
        tags: [{ id: "tag-1", name: "Tranh dân gian", slug: "tranh-dan-gian" }],
        likeCount: 4,
        commentCount: 2,
        viewerHasLiked: false,
        viewerHasBookmarked: false,
        relatedWork: { id: "work-1", title: "Gốm làng cổ", slug: "gom-lang-co" },
        images: [{
          id: "image-1",
          url: "/api/v1/community/posts/chuyen-di-lang-co/media/image-1",
        }],
      },
    ],
    meta: { requestId: "feed-1", page: 2, pageSize: 10, total: 25 },
  });
});

describe("CommunityFeed", () => {
  it("filters categories, keeps the current filter in pagination, and escapes text", async () => {
    render(<CommunityFeed page={2} category="heritage-culture" />, {
      wrapper,
    });

    expect(
      await screen.findByRole("heading", {
        name: "Chuyện đi làng cổ <img src=x onerror=alert(1)>",
      }),
    ).toBeDefined();
    const image = screen.getByRole("img", {
      name: "Chuyện đi làng cổ <img src=x onerror=alert(1)> — ảnh đính kèm 1",
    });
    expect(image.getAttribute("src")).toBe(
      "/api/v1/community/posts/chuyen-di-lang-co/media/image-1",
    );
    expect(screen.getByRole("link", { name: "Tác phẩm liên quan: Gốm làng cổ" }).getAttribute("href")).toBe("/works/gom-lang-co");
    expect(screen.getByText("Thành viên cộng đồng")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Di sản và văn hóa" })
        .getAttribute("href"),
    ).toBe("/community?category=heritage-culture&page=1");
    expect(
      screen.getByRole("link", { name: "Trang trước" }).getAttribute("href"),
    ).toBe("/community?category=heritage-culture&page=1");
    expect(
      screen.getByRole("link", { name: "Trang sau" }).getAttribute("href"),
    ).toBe("/community?category=heritage-culture&page=3");
    expect(api.posts).toHaveBeenCalledWith(
      expect.objectContaining({ page: 2, category: "heritage-culture" }),
      expect.any(AbortSignal),
    );
  });

  it("combines search, tag, work, category and sort filters in URL based controls", async () => {
    render(
      <CommunityFeed
        page={2}
        category="heritage-culture"
        tag="tranh-dan-gian"
        q="tranh Đông Hồ"
        sort="discussed"
        relatedWorkId="work-1"
      />,
      { wrapper },
    );

    await screen.findByRole("heading", { name: "Cộng đồng" });
    await screen.findByRole("link", { name: /Tranh dân gian/ });
    expect(api.posts).toHaveBeenCalledWith(
      {
        page: 2,
        category: "heritage-culture",
        tag: "tranh-dan-gian",
        q: "tranh Đông Hồ",
        sort: "discussed",
        relatedWorkId: "work-1",
      },
      expect.any(AbortSignal),
    );
    expect((screen.getByRole("searchbox", { name: "Tìm kiếm bài viết" }) as HTMLInputElement).value).toBe("tranh Đông Hồ");
    expect(screen.getByRole("link", { name: "Thảo luận nhiều" }).getAttribute("href")).toContain("sort=discussed");
    expect(screen.getByRole("link", { name: "#Tranh dân gian" }).getAttribute("href")).toContain("tag=tranh-dan-gian");
    expect(screen.getByRole("link", { name: "Trang sau" }).getAttribute("href")).toContain("relatedWorkId=work-1");
  });

  it("shows a clear empty state when a selected category has no posts", async () => {
    api.posts.mockResolvedValueOnce({
      success: true,
      data: [],
      meta: { requestId: "feed-empty", page: 1, pageSize: 20, total: 0 },
    });
    render(<CommunityFeed page={1} category="sharing-experiences" />, {
      wrapper,
    });

    expect(
      await screen.findByText("Chưa có bài viết trong chuyên mục này."),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Viết bài đầu tiên" })).toBeDefined();
  });

  it("does not render an image URL unless it matches the backend community delivery path", async () => {
    api.posts.mockResolvedValueOnce({
      success: true,
      data: [{
        id: "post-2",
        slug: "bai-viet-cong-khai",
        title: "Bài viết công khai",
        excerpt: null,
        category: { id: "cat-1", name: "Di sản", slug: "di-san" },
        author: { displayName: "Thành viên" },
        publishedAt: "2026-10-13T09:00:00Z",
        likeCount: 0,
        commentCount: 0,
        viewerHasLiked: false,
        viewerHasBookmarked: false,
        relatedWork: null,
        images: [{ id: "image-2", url: "https://tracker.example.test/pixel.png" }],
      }],
      meta: { requestId: "feed-image-url", page: 1, pageSize: 20, total: 1 },
    });
    render(<CommunityFeed page={1} />, { wrapper });

    await screen.findByRole("heading", { name: "Bài viết công khai" });
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("exposes a retry action when the feed cannot load", async () => {
    const user = userEvent.setup();
    api.posts
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({
        success: true,
        data: [],
        meta: { requestId: "feed-retry", page: 1, pageSize: 20, total: 0 },
      });
    render(<CommunityFeed page={1} />, { wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Thử tải lại" }),
    );
    expect(await screen.findByText("Chưa có bài viết nào.")).toBeDefined();
  });

  it("scopes personalized feed data to the current viewer", async () => {
    render(<CommunityFeed page={1} />, { wrapper });

    await screen.findByRole("heading", { name: "Cộng đồng" });
    expect(
      queryClient.getQueryCache().getAll().some((query) =>
        query.queryKey.some(
          (part) =>
            typeof part === "object" &&
            part !== null &&
            "viewerKey" in part &&
            part.viewerKey === "viewer-7",
        ),
      ),
    ).toBe(true);
  });
});
