import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityMemberProfile } from "@/components/community/community-member-profile";

const api = vi.hoisted(() => ({
  profile: vi.fn(),
  posts: vi.fn(),
  follow: vi.fn(),
  unfollow: vi.fn(),
  updateProfile: vi.fn(),
  followers: vi.fn(),
  following: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { id: "viewer-1" } }));

vi.mock("@/lib/api/client", () => ({ communityMemberApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));

const member = {
  id: "member-2",
  username: "lan-anh",
  displayName: "Lan Anh",
  avatarUrl: null,
  bio: "Ghi lại chuyện làng và những người tôi gặp.",
  joinedAt: "2024-06-01T09:00:00Z",
  publishedPostCount: 21,
  followerCount: 9,
  followingCount: 4,
  viewerIsFollowing: false,
};

const memberPost = {
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
  viewerHasBookmarked: false,
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
  api.profile.mockResolvedValue(member);
  api.posts.mockResolvedValue({
    success: true,
    data: [memberPost],
    meta: { requestId: "member-posts", page: 1, pageSize: 20, total: 21 },
  });
  api.follow.mockResolvedValue({
    memberId: "member-2",
    isFollowing: true,
    followerCount: 10,
  });
  api.unfollow.mockResolvedValue({
    memberId: "member-2",
    isFollowing: false,
    followerCount: 9,
  });
  api.updateProfile.mockImplementation((input) => Promise.resolve({ ...member, ...input }));
  api.followers.mockResolvedValue({
    success: true,
    data: [{ id: "member-3", username: "minh", displayName: "Minh", avatarUrl: null, viewerIsFollowing: false }],
    meta: { requestId: "followers", page: 1, pageSize: 20, total: 1 },
  });
  api.following.mockResolvedValue({
    success: true,
    data: [],
    meta: { requestId: "following", page: 1, pageSize: 20, total: 0 },
  });
});

describe("CommunityMemberProfile", () => {
  it("shows the safe community profile, published posts, and follow state", async () => {
    const user = userEvent.setup();
    render(<CommunityMemberProfile username="lan-anh" />, { wrapper });

    expect(await screen.findByRole("heading", { name: "Lan Anh" })).toBeDefined();
    expect(screen.getByText("Ghi lại chuyện làng và những người tôi gặp.")).toBeDefined();
    expect(screen.getAllByText("Người theo dõi").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Người theo dõi 9" })).toBeDefined();
    expect(await screen.findByRole("heading", { name: "Ký ức làng cổ" })).toBeDefined();
    expect(screen.queryByText(/@example\.com|Số điện thoại/i)).toBeNull();
    expect(api.profile).toHaveBeenCalledWith("lan-anh", expect.any(AbortSignal));
    expect(api.posts).toHaveBeenCalledWith("lan-anh", 1, expect.any(AbortSignal));

    await user.click(screen.getByRole("button", { name: "Theo dõi" }));
    expect(await screen.findByRole("button", { name: "Đang theo dõi" })).toBeDefined();
    expect(api.follow).toHaveBeenCalledWith("member-2");
    expect(screen.getByRole("link", { name: "Người theo dõi 10" })).toBeDefined();
  });

  it("paginates only the member's published posts", async () => {
    api.posts.mockImplementation((_username: string, page: number) =>
      Promise.resolve({
        success: true,
        data: [memberPost],
        meta: {
          requestId: `member-page-${page}`,
          page,
          pageSize: 20,
          total: 21,
        },
      }),
    );
    render(<CommunityMemberProfile username="lan-anh" />, { wrapper });

    const nextPage = await screen.findByRole("link", { name: "Trang sau" });
    expect(nextPage.getAttribute("href")).toBe("/community/members/lan-anh?page=2");
  });

  it("does not offer a self-follow action", async () => {
    auth.user = { id: "member-2" };
    api.profile.mockResolvedValue({ ...member, viewerIsFollowing: false });
    render(<CommunityMemberProfile username="lan-anh" />, { wrapper });

    expect(await screen.findByRole("heading", { name: "Lan Anh" })).toBeDefined();
    expect(screen.queryByRole("button", { name: /theo dõi/i })).toBeNull();
  });

  it("lets the owner edit only community identity fields", async () => {
    const user = userEvent.setup();
    auth.user = { id: "member-2" };
    render(<CommunityMemberProfile username="lan-anh" />, { wrapper });

    await user.click(await screen.findByRole("button", { name: "Chỉnh sửa hồ sơ" }));
    await user.clear(screen.getByRole("textbox", { name: "Tên hiển thị" }));
    await user.type(screen.getByRole("textbox", { name: "Tên hiển thị" }), "Lan Anh mới");
    await user.click(screen.getByRole("button", { name: "Lưu hồ sơ" }));

    expect(api.updateProfile).toHaveBeenCalledWith(expect.objectContaining({ displayName: "Lan Anh mới" }));
    expect(await screen.findByRole("heading", { name: "Lan Anh mới" })).toBeDefined();
  });

  it("shows the public follower list and exposes follower/following links", async () => {
    render(<CommunityMemberProfile username="lan-anh" view="followers" />, { wrapper });

    expect(await screen.findByRole("heading", { name: "Người theo dõi của Lan Anh" })).toBeDefined();
    expect(await screen.findByRole("link", { name: "Minh" })).toBeDefined();
    expect(api.followers).toHaveBeenCalledWith("lan-anh", 1, expect.any(AbortSignal));
    expect(screen.getByRole("link", { name: "Đang theo dõi 4" })).toBeDefined();
  });
});
