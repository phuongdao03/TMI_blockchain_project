import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityPostEngagement } from "@/components/community/community-post-engagement";

const api = vi.hoisted(() => ({
  comments: vi.fn(),
  createComment: vi.fn(),
  updateComment: vi.fn(),
  deleteComment: vi.fn(),
  likePost: vi.fn(),
  unlikePost: vi.fn(),
  bookmarkPost: vi.fn(),
  unbookmarkPost: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { id: "viewer-1" } as { id: string } | null }));

vi.mock("@/lib/api/client", () => ({ communityApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));

const commentThread = {
  id: "comment-1",
  parentId: null,
  content: "Chia sẻ hay <script>không chạy</script>",
  author: {
    id: "viewer-1",
    username: "lan-anh",
    displayName: "Lan Anh",
    avatarUrl: null,
  },
  createdAt: "2026-10-13T09:00:00Z",
  replies: [
    {
      id: "reply-1",
      parentId: "comment-1",
      content: "Mình cũng từng ghé nơi này.",
      author: {
        id: "member-2",
        username: "minh-an",
        displayName: "Minh An",
        avatarUrl: null,
      },
      createdAt: "2026-10-13T10:00:00Z",
    },
  ],
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function renderEngagement() {
  return render(
    <CommunityPostEngagement
      post={{
        id: "post-1",
        slug: "ky-uc-lang-co",
        likeCount: 10,
        commentCount: 1,
        viewerHasLiked: false,
        viewerHasBookmarked: false,
      }}
    />,
    { wrapper },
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: "viewer-1" };
  api.comments.mockResolvedValue({
    success: true,
    data: [commentThread],
    meta: { requestId: "comments-1", page: 1, pageSize: 20, total: 1 },
  });
  api.createComment.mockImplementation((_postId, input) =>
    Promise.resolve({
      id: input.parentId ? "reply-2" : "comment-2",
      postId: "post-1",
      parentId: input.parentId ?? null,
      content: input.content,
      author: {
        id: "viewer-1",
        username: "viewer",
        displayName: "Thành viên",
        avatarUrl: null,
      },
      createdAt: "2026-10-13T11:00:00Z",
      isDeleted: false,
    }),
  );
  api.updateComment.mockImplementation((commentId, input) =>
    Promise.resolve({
      ...commentThread,
      id: commentId,
      content: input.content,
      isDeleted: false,
    }),
  );
  api.deleteComment.mockResolvedValue(undefined);
  api.likePost.mockResolvedValue({
    postId: "post-1",
    likeCount: 11,
    isLiked: true,
  });
  api.unlikePost.mockResolvedValue({
    postId: "post-1",
    likeCount: 10,
    isLiked: false,
  });
  api.bookmarkPost.mockResolvedValue({ postId: "post-1", isBookmarked: true });
  api.unbookmarkPost.mockResolvedValue({
    postId: "post-1",
    isBookmarked: false,
  });
});

describe("CommunityPostEngagement", () => {
  it("renders thread replies as text and updates like and bookmark state", async () => {
    const user = userEvent.setup();
    renderEngagement();

    expect(await screen.findByText("Chia sẻ hay <script>không chạy</script>")).toBeDefined();
    expect(screen.getByRole("link", { name: "Lan Anh" }).getAttribute("href")).toBe(
      "/community/members/lan-anh",
    );
    expect(screen.getByText("Mình cũng từng ghé nơi này.")).toBeDefined();
    expect(document.querySelector("script")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Thích bài viết" }));
    expect(await screen.findByRole("button", { name: "Bỏ thích bài viết" })).toBeDefined();
    expect(api.likePost).toHaveBeenCalledWith("post-1");
    expect(screen.getByText("11 lượt thích")).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Lưu bài viết" }));
    expect(await screen.findByRole("button", { name: "Đã lưu bài viết" })).toBeDefined();
    expect(api.bookmarkPost).toHaveBeenCalledWith("post-1");
  });

  it("posts a new thread and lets members reply to a nested comment", async () => {
    const user = userEvent.setup();
    renderEngagement();

    await user.type(await screen.findByLabelText("Bình luận của bạn"), "Ý kiến mới");
    await user.click(screen.getByRole("button", { name: "Gửi bình luận" }));

    await waitFor(() =>
      expect(api.createComment).toHaveBeenCalledWith("post-1", {
        content: "Ý kiến mới",
      }),
    );
    expect(await screen.findByText("Ý kiến mới")).toBeDefined();

    const originalRoot = screen.getByText("Chia sẻ hay <script>không chạy</script>").closest("article");
    expect(originalRoot).not.toBeNull();
    expect(screen.getByText("Mình cũng từng ghé nơi này.")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Trả lời Minh An" }));
    await user.type(await screen.findByLabelText("Nội dung trả lời"), "Một phản hồi");
    await user.click(screen.getByRole("button", { name: "Gửi trả lời" }));

    await waitFor(() =>
      expect(api.createComment).toHaveBeenLastCalledWith("post-1", {
        content: "Một phản hồi",
        parentId: "reply-1",
      }),
    );
    expect(await screen.findByText("Một phản hồi")).toBeDefined();
  });

  it("lets only the author edit and delete a comment, preserving replies as a tombstone", async () => {
    const user = userEvent.setup();
    renderEngagement();

    expect(await screen.findByText("Chia sẻ hay <script>không chạy</script>")).toBeDefined();
    expect(screen.getAllByRole("button", { name: "Chỉnh sửa bình luận" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Xóa bình luận" })).toHaveLength(1);

    await user.click(screen.getByRole("button", { name: "Chỉnh sửa bình luận" }));
    const editor = screen.getByRole("textbox", { name: "Chỉnh sửa bình luận" });
    await user.clear(editor);
    await user.type(editor, "Nội dung đã chỉnh sửa");
    await user.click(screen.getByRole("button", { name: "Lưu chỉnh sửa" }));

    await waitFor(() =>
      expect(api.updateComment).toHaveBeenCalledWith("comment-1", {
        content: "Nội dung đã chỉnh sửa",
      }),
    );
    expect(await screen.findByText("Nội dung đã chỉnh sửa")).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Xóa bình luận" }));
    expect(api.deleteComment).toHaveBeenCalledWith("comment-1");
    expect(await screen.findByText("Bình luận đã bị xóa.")).toBeDefined();
    expect(screen.getByText("Mình cũng từng ghé nơi này.")).toBeDefined();
    expect(screen.queryByRole("link", { name: "Lan Anh" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Chỉnh sửa bình luận" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Xóa bình luận" })).toBeNull();
  });

  it("asks visitors to sign in before posting or changing relations", async () => {
    auth.user = null;
    renderEngagement();

    expect(await screen.findByRole("link", { name: "Đăng nhập để tham gia" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Gửi bình luận" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Thích bài viết" })).toBeNull();
  });
});
