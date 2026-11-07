import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityPostFollowAction } from "@/components/community/community-post-follow-action";

const api = vi.hoisted(() => ({
  postFollowState: vi.fn(),
  followPost: vi.fn(),
  unfollowPost: vi.fn(),
}));
const auth = vi.hoisted(() => ({
  user: { id: "member-1" } as { id: string } | null,
  status: "authenticated" as
    | "authenticated"
    | "unauthenticated"
    | "loading"
    | "error",
}));

vi.mock("@/lib/api/client", () => ({ communityApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
  useAuthStatus: () => auth.status,
}));

let queryClient: QueryClient;

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  vi.clearAllMocks();
  auth.user = { id: "member-1" };
  auth.status = "authenticated";
  api.postFollowState.mockResolvedValue({
    postId: "post-1",
    isFollowing: false,
  });
  api.followPost.mockResolvedValue({
    postId: "post-1",
    isFollowing: true,
  });
  api.unfollowPost.mockResolvedValue({
    postId: "post-1",
    isFollowing: false,
  });
});

describe("CommunityPostFollowAction", () => {
  it("follows a topic and reflects the server-confirmed state", async () => {
    render(
      <CommunityPostFollowAction postId="post-1" slug="heritage-story" />,
      { wrapper },
    );

    const followButton = await screen.findByRole("button", {
      name: "Theo dõi chủ đề",
    });
    fireEvent.click(followButton);

    const followedButton = await screen.findByRole("button", {
      name: "Đang theo dõi chủ đề",
    });
    expect(followedButton.getAttribute("aria-pressed")).toBe("true");
    expect(api.followPost).toHaveBeenCalledWith("post-1");
  });

  it("offers a safe login return when the visitor is signed out", () => {
    auth.user = null;
    auth.status = "unauthenticated";

    render(
      <CommunityPostFollowAction postId="post-1" slug="heritage-story" />,
      { wrapper },
    );

    expect(
      screen.getByRole("link", { name: "Đăng nhập để theo dõi chủ đề" })
        .getAttribute("href"),
    ).toBe("/login?next=%2Fcommunity%2Fposts%2Fheritage-story");
  });
});
