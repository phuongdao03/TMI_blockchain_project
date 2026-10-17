import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityCommentThreads } from "@/components/community/community-comment-threads";

const api = vi.hoisted(() => ({
  comments: vi.fn(),
  createComment: vi.fn(),
  updateComment: vi.fn(),
  deleteComment: vi.fn(),
  likeComment: vi.fn(),
  unlikeComment: vi.fn(),
}));
const auth = vi.hoisted(() => ({ user: { id: "viewer-1" } }));
vi.mock("@/lib/api/client", () => ({ communityApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  auth.user = { id: "viewer-1" };
  api.comments.mockResolvedValue({
    success: true,
    data: [
      {
        id: "comment-1",
        parentId: null,
        content: "Góc nhìn hay",
        isDeleted: false,
        createdAt: "2026-10-14T10:00:00Z",
        likeCount: 2,
        viewerHasLiked: false,
        author: {
          id: "author-1",
          username: "lan-anh",
          displayName: "Lan Anh",
          avatarUrl: null,
          roleLabel: "Thẩm định viên",
        },
        replies: [],
      },
    ],
    meta: { requestId: "comments", page: 1, pageSize: 20, total: 1 },
  });
  api.likeComment.mockResolvedValue({
    commentId: "comment-1",
    likeCount: 3,
    isLiked: true,
  });
  api.unlikeComment.mockResolvedValue({
    commentId: "comment-1",
    likeCount: 2,
    isLiked: false,
  });
});

describe("CommunityCommentThreads", () => {
  it("loads and toggles oldest/newest order while retaining page", async () => {
    const user = userEvent.setup();
    render(<CommunityCommentThreads postId="post-1" commentCount={1} />, {
      wrapper,
    });

    await screen.findByText("Góc nhìn hay");
    expect(screen.queryByText("Thẩm định viên")).toBeNull();
    expect(document.getElementById("community-comments-title")).not.toBeNull();
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Sắp xếp bình luận" }),
      "newest",
    );

    await waitFor(() =>
      expect(api.comments).toHaveBeenLastCalledWith(
        "post-1",
        1,
        expect.any(AbortSignal),
        "newest",
      ),
    );
  });

  it("lets a signed-in reader like a live comment and updates the count", async () => {
    const user = userEvent.setup();
    render(<CommunityCommentThreads postId="post-1" commentCount={1} />, {
      wrapper,
    });

    const likeButton = await screen.findByRole("button", {
      name: "Thích bình luận (2)",
    });
    await user.click(likeButton);

    expect(api.likeComment).toHaveBeenCalledWith("comment-1");
    expect(
      await screen.findByRole("button", { name: "Bỏ thích bình luận (3)" }),
    ).toBeDefined();
  });

  it("lets members reply to deeper comments and keeps the conversation flat", async () => {
    const user = userEvent.setup();
    api.comments.mockResolvedValue({
      success: true,
      data: [
        {
          id: "comment-1",
          parentId: null,
          content: "Root comment",
          isDeleted: false,
          createdAt: "2026-10-14T10:00:00Z",
          likeCount: 0,
          viewerHasLiked: false,
          author: {
            id: "author-1",
            username: "lan-anh",
            displayName: "Lan Anh",
            avatarUrl: null,
          },
          replies: [
            {
              id: "comment-2",
              parentId: "comment-1",
              content: "First reply",
              isDeleted: false,
              createdAt: "2026-10-14T10:01:00Z",
              likeCount: 0,
              viewerHasLiked: false,
              author: {
                id: "author-2",
                username: "minh",
                displayName: "Minh",
                avatarUrl: null,
              },
            },
            {
              id: "comment-3",
              parentId: "comment-2",
              content: "Deeper reply",
              isDeleted: false,
              createdAt: "2026-10-14T10:02:00Z",
              likeCount: 0,
              viewerHasLiked: false,
              author: {
                id: "author-3",
                username: "hoa",
                displayName: "Hoa",
                avatarUrl: null,
              },
            },
          ],
        },
      ],
      meta: { requestId: "comments", page: 1, pageSize: 20, total: 1 },
    });
    api.createComment.mockResolvedValue({
      id: "comment-4",
      postId: "post-1",
      parentId: "comment-2",
      content: "Third reply",
      author: {
        id: "viewer-1",
        username: "viewer",
        displayName: "Reader",
        avatarUrl: null,
      },
      isDeleted: false,
      createdAt: "2026-10-14T10:03:00Z",
      likeCount: 0,
      viewerHasLiked: false,
    });
    render(<CommunityCommentThreads postId="post-1" commentCount={3} />, {
      wrapper,
    });

    await screen.findByText("Deeper reply");
    await user.click(screen.getByRole("button", { name: "Trả lời Minh" }));
    await user.type(screen.getByLabelText("Nội dung trả lời"), "Third reply");
    await user.click(screen.getByRole("button", { name: "Gửi trả lời" }));

    await waitFor(() =>
      expect(api.createComment).toHaveBeenCalledWith("post-1", {
        content: "Third reply",
        parentId: "comment-2",
      }),
    );
    expect(await screen.findByText("Third reply")).toBeDefined();
  });
});
