import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/community/community-member-profile", () => ({
  CommunityMemberProfile: ({
    username,
    page,
    view,
  }: {
    username: string;
    page: number;
    view: string;
  }) => <div data-username={username} data-page={page} data-view={view} />,
}));

import CommunityMemberPage from "@/app/(public)/community/members/[username]/page";

describe("CommunityMemberPage", () => {
  it("passes the URL username to the public member view", async () => {
    const page = await CommunityMemberPage({
      params: Promise.resolve({ username: "lan-anh" }),
      searchParams: Promise.resolve({ page: "2" }),
    });

    expect(page.props.username).toBe("lan-anh");
    expect(page.props.page).toBe(2);
    expect(page.props.view).toBe("posts");
  });

  it("passes follower or following view from the canonical query string", async () => {
    const page = await CommunityMemberPage({
      params: Promise.resolve({ username: "lan-anh" }),
      searchParams: Promise.resolve({ page: "3", view: "following" }),
    });

    expect(page.props.page).toBe(3);
    expect(page.props.view).toBe("following");
  });
});
