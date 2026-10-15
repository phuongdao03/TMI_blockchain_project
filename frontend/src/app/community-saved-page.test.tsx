import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ getServerAuthState: vi.fn() }));
const navigation = vi.hoisted(() => ({ redirect: vi.fn() }));

vi.mock("@/lib/auth/server-session", () => auth);
vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));
vi.mock("@/components/community/community-saved-posts", () => ({
  CommunitySavedPosts: () => <div data-testid="saved-posts" />,
}));

import CommunitySavedPage from "@/app/(public)/community/saved/page";

describe("CommunitySavedPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects unauthenticated visitors to sign in", async () => {
    auth.getServerAuthState.mockResolvedValue({
      user: null,
      hasRefreshCookie: false,
    });

    await CommunitySavedPage({ searchParams: Promise.resolve({ page: "2" }) });

    expect(navigation.redirect).toHaveBeenCalledWith(
      "/login?next=%2Fcommunity%2Fsaved",
    );
  });

  it("renders the saved list for an authenticated session", async () => {
    auth.getServerAuthState.mockResolvedValue({
      user: { id: "viewer-1" },
      hasRefreshCookie: true,
    });

    const page = await CommunitySavedPage({
      searchParams: Promise.resolve({ page: "2" }),
    });

    expect(navigation.redirect).not.toHaveBeenCalled();
    expect(page.props.page).toBe(2);
  });
});
