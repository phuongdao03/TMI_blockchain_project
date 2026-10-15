import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CommunityAdminCommentsWorkspace,
  CommunityAdminMembersWorkspace,
  CommunityAdminPostsWorkspace,
} from "@/components/community/community-admin-content-workspaces";

const api = vi.hoisted(() => ({
  workspacePosts: vi.fn(),
  pinPost: vi.fn(),
  workspaceComments: vi.fn(),
  hideWorkspaceComment: vi.fn(),
  members: vi.fn(),
  memberRestrictions: vi.fn(),
  createMemberRestriction: vi.fn(),
  revokeMemberRestriction: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ communityAdminApi: api }));

describe("community admin content workspaces", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("filters posts and submits a reasoned pin action", async () => {
    const user = userEvent.setup();
    api.workspacePosts.mockResolvedValue(page([post]));
    api.pinPost.mockResolvedValue({ postId: post.id, isPinned: true });

    renderWithQuery(<CommunityAdminPostsWorkspace />);

    expect(
      await screen.findByRole("heading", { name: post.title }),
    ).toBeDefined();
    expect(
      screen.getByText(
        (_content, element) => element?.textContent === post.content,
      ),
    ).toBeDefined();
    await user.type(screen.getByLabelText("Từ khóa"), "gốm");
    await user.click(screen.getByRole("button", { name: "Tìm bài viết" }));
    await waitFor(() =>
      expect(api.workspacePosts.mock.calls.at(-1)?.[0]).toEqual({
        q: "gốm",
        status: undefined,
        page: 1,
        pageSize: 20,
      }),
    );

    await user.type(
      screen.getByLabelText("Lý do kiểm duyệt"),
      "Nội dung đã được đối chiếu.",
    );
    await user.click(screen.getByRole("button", { name: "Ghim bài viết" }));
    await waitFor(() =>
      expect(api.pinPost).toHaveBeenCalledWith(post.id, {
        reason: "Nội dung đã được đối chiếu.",
      }),
    );
  });

  it("does not offer moderator restore for posts deleted by their owner", async () => {
    api.workspacePosts.mockResolvedValue(page([ownerDeletedPost]));

    renderWithQuery(<CommunityAdminPostsWorkspace />);

    expect(
      await screen.findByRole("heading", { name: ownerDeletedPost.title }),
    ).toBeDefined();
    expect(
      screen.queryByRole("button", { name: "Khôi phục bài viết" }),
    ).toBeNull();
    expect(screen.getByText(/Tác giả đã xóa bài viết/)).toBeDefined();
  });

  it("moderates a comment while retaining its public post context", async () => {
    const user = userEvent.setup();
    api.workspaceComments.mockResolvedValue(page([comment]));
    api.hideWorkspaceComment.mockResolvedValue({
      commentId: comment.id,
      visibility: "HIDDEN",
    });

    renderWithQuery(<CommunityAdminCommentsWorkspace />);

    expect(await screen.findByText(comment.content)).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: comment.post.title })
        .getAttribute("href"),
    ).toBe(`/community/posts/${comment.post.slug}`);
    await user.type(
      screen.getByLabelText("Lý do kiểm duyệt"),
      "Bình luận vi phạm nội quy.",
    );
    await user.click(screen.getByRole("button", { name: "Ẩn bình luận" }));

    await waitFor(() =>
      expect(api.hideWorkspaceComment).toHaveBeenCalledWith(comment.id, {
        reason: "Bình luận vi phạm nội quy.",
      }),
    );
  });

  it("applies and revokes a member restriction with separate audit reasons", async () => {
    const user = userEvent.setup();
    api.members.mockResolvedValue(page([member]));
    api.memberRestrictions.mockResolvedValue(page([restriction]));
    api.createMemberRestriction.mockResolvedValue(restriction);
    api.revokeMemberRestriction.mockResolvedValue({
      ...restriction,
      status: "REVOKED",
    });

    renderWithQuery(<CommunityAdminMembersWorkspace />);

    await user.click(
      await screen.findByRole("button", { name: "Lịch sử và hạn chế" }),
    );
    expect(
      await screen.findByText(
        (_content, element) =>
          element?.tagName === "P" && element.textContent.includes("request-1"),
      ),
    ).toBeDefined();

    await user.type(screen.getByLabelText("Lý do"), "Tạm dừng để rà soát.");
    await user.click(screen.getByRole("button", { name: "Áp dụng hạn chế" }));
    await waitFor(() =>
      expect(api.createMemberRestriction).toHaveBeenCalledWith(
        member.member.id,
        {
          scope: "POSTS",
          durationMinutes: 60,
          reason: "Tạm dừng để rà soát.",
        },
      ),
    );

    await user.type(
      screen.getByLabelText("Lý do thu hồi"),
      "Đã hoàn tất rà soát.",
    );
    await user.click(screen.getByRole("button", { name: "Thu hồi hạn chế" }));
    await waitFor(() =>
      expect(api.revokeMemberRestriction).toHaveBeenCalledWith(
        member.member.id,
        restriction.id,
        { reason: "Đã hoàn tất rà soát." },
      ),
    );
  });
});

function renderWithQuery(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function page<T>(data: T[]) {
  return {
    data,
    meta: { requestId: "test", page: 1, pageSize: 20, total: data.length },
  };
}

const author = {
  id: "member-1",
  username: "lan-anh",
  displayName: "Lan Anh",
  avatarUrl: null,
};
const post = {
  id: "post-1",
  slug: "goc-lang-nghe",
  title: "Góc làng nghề",
  excerpt: "Một câu chuyện về gốm.",
  content: "Nội dung đầy đủ để kiểm duyệt.\nAn toàn dưới dạng văn bản thuần.",
  category: { id: "category-1", name: "Làng nghề", slug: "lang-nghe" },
  author,
  publishedAt: "2026-10-15T09:00:00Z",
  likeCount: 2,
  commentCount: 1,
  viewCount: 10,
  viewerHasLiked: false,
  viewerHasBookmarked: false,
  tags: [],
  relatedWork: null,
  images: [],
  status: "PUBLISHED" as const,
  isPinned: false,
  commentsLocked: false,
  deletedAt: null,
  preDeleteStatus: null,
};
const comment = {
  id: "comment-1",
  content: "Cảm ơn vì đã chia sẻ.",
  author,
  isDeleted: false,
  createdAt: "2026-10-15T10:00:00Z",
  likeCount: 0,
  viewerHasLiked: false,
  visibility: "VISIBLE" as const,
  post: { id: post.id, slug: post.slug, title: post.title },
};
const ownerDeletedPost = {
  ...post,
  id: "post-owner-deleted",
  title: "Bài do tác giả xóa",
  status: "DELETED" as const,
  deletedAt: "2026-10-15T12:00:00Z",
  preDeleteStatus: null,
};
const member = {
  member: author,
  publishedPostCount: 3,
  commentCount: 5,
  followerCount: 8,
  followingCount: 4,
  lastActivityAt: "2026-10-15T10:00:00Z",
  activeRestrictions: [],
};
const restriction = {
  id: "restriction-1",
  member: author,
  scope: "POSTS" as const,
  status: "ACTIVE" as const,
  reason: "Đang rà soát.",
  startsAt: "2026-10-15T10:00:00Z",
  expiresAt: "2026-10-15T11:00:00Z",
  actor: {
    id: "admin-1",
    username: "moderator",
    displayName: "Điều phối viên",
    avatarUrl: null,
  },
  requestId: "request-1",
};
