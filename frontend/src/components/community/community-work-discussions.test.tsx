import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityWorkDiscussions } from "@/components/community/community-work-discussions";

const communityApi = vi.hoisted(() => ({ posts: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ communityApi }));

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  communityApi.posts.mockResolvedValue({
    data: [],
    meta: { requestId: "discussion", page: 1, pageSize: 5, total: 0 },
  });
});

describe("CommunityWorkDiscussions", () => {
  it("uses the published work ID and links the discussion and preselected composer", async () => {
    render(
      <CommunityWorkDiscussions
        workId="work-1"
        workSlug="gom-lang-co"
        workTitle="Gốm làng cổ"
      />,
      { wrapper },
    );

    expect(communityApi.posts).toHaveBeenCalledWith(
      { relatedWorkId: "work-1", page: 1, pageSize: 5, sort: "discussed" },
      expect.anything(),
    );
    expect(
      await screen.findByRole("heading", { name: "Thảo luận cộng đồng" }),
    ).toBeDefined();
    expect(
      await screen.findByText(/bài viết dưới đây do thành viên chia sẻ/i),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Xem tất cả thảo luận" })
        .getAttribute("href"),
    ).toBe("/community?relatedWorkId=work-1");
    expect(
      screen
        .getByRole("link", { name: "Viết bài thảo luận về Gốm làng cổ" })
        .getAttribute("href"),
    ).toBe("/community/new?relatedWorkId=work-1&relatedWorkSlug=gom-lang-co");
  });
});
