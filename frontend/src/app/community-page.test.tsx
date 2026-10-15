import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/community/community-feed", () => ({
  CommunityFeed: (props: Record<string, unknown>) => <div data-props={JSON.stringify(props)} />,
}));

import CommunityPage from "@/app/(public)/community/page";

describe("CommunityPage query state", () => {
  it("passes bounded discovery filters to the feed", async () => {
    const page = await CommunityPage({
      searchParams: Promise.resolve({
        page: "4",
        category: "heritage-culture",
        tag: "dong-ho",
        q: "  tranh Đông Hồ  ",
        sort: "discussed",
        relatedWorkId: "public-work-1",
      }),
    });

    expect(page.props).toEqual({
      category: "heritage-culture",
      page: 4,
      tag: "dong-ho",
      q: "tranh Đông Hồ",
      sort: "discussed",
      relatedWorkId: "public-work-1",
    });
  });

  it("falls back to recent when the sort value is outside the contract", async () => {
    const page = await CommunityPage({
      searchParams: Promise.resolve({ sort: "admin" }),
    });

    expect(page.props.sort).toBe("recent");
  });
});
