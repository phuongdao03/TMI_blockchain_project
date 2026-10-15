import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ getServerAuthState: vi.fn() }));
const navigation = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock("@/lib/auth/server-session", () => auth);
vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));
vi.mock("@/components/community/community-mine-posts", () => ({
  CommunityMinePosts: (props: Record<string, unknown>) => <div data-props={JSON.stringify(props)} />,
}));

import CommunityMinePage from "@/app/(public)/community/mine/page";

describe("CommunityMinePage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("requires the existing website session", async () => {
    auth.getServerAuthState.mockResolvedValue({ user: null, hasRefreshCookie: false });

    await CommunityMinePage({ searchParams: Promise.resolve({ status: "DRAFT", page: "2" }) });

    expect(navigation.redirect).toHaveBeenCalledWith("/login?next=%2Fcommunity%2Fmine%3Fstatus%3DDRAFT%26page%3D2");
  });

  it("passes valid owner status and page to the workspace", async () => {
    auth.getServerAuthState.mockResolvedValue({ user: { id: "member-1" }, hasRefreshCookie: true });

    const page = await CommunityMinePage({ searchParams: Promise.resolve({ status: "PUBLISHED", page: "3" }) });

    expect(page.props).toMatchObject({ status: "PUBLISHED", page: 3 });
  });

  it("ignores an unsupported owner status", async () => {
    auth.getServerAuthState.mockResolvedValue({ user: { id: "member-1" }, hasRefreshCookie: true });

    const page = await CommunityMinePage({ searchParams: Promise.resolve({ status: "DELETED" }) });

    expect(page.props.status).toBeUndefined();
  });
});
