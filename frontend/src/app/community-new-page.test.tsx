import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ getServerAuthState: vi.fn() }));
const navigation = vi.hoisted(() => ({ redirect: vi.fn() }));
const publicWork = vi.hoisted(() => ({ loadPublicWork: vi.fn() }));

vi.mock("@/lib/auth/server-session", () => auth);
vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));
vi.mock("@/lib/api/public-work-server", () => publicWork);

import CommunityNewPage from "@/app/(public)/community/new/page";

describe("CommunityNewPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends visitors to sign in before showing the authenticated editor", async () => {
    auth.getServerAuthState.mockResolvedValue({
      user: null,
      hasRefreshCookie: false,
    });

    await CommunityNewPage({ searchParams: Promise.resolve({}) });

    expect(navigation.redirect).toHaveBeenCalledWith(
      "/login?next=%2Fcommunity%2Fnew",
    );
  });

  it("prefills only a published work whose ID matches the public slug lookup", async () => {
    auth.getServerAuthState.mockResolvedValue({
      user: { id: "member-1" },
      hasRefreshCookie: true,
    });
    publicWork.loadPublicWork.mockResolvedValue({
      kind: "detail",
      detail: {
        id: "work-1",
        title: "Gốm làng cổ",
        canonicalSlug: "gom-lang-co",
      },
    });

    const page = await CommunityNewPage({
      searchParams: Promise.resolve({
        postId: "post-1",
        relatedWorkId: "work-1",
        relatedWorkSlug: "gom-lang-co",
      }),
    });

    expect(page.props).toMatchObject({
      postId: "post-1",
      relatedWork: { id: "work-1", title: "Gốm làng cổ", slug: "gom-lang-co" },
    });
  });

  it("does not trust an arbitrary related work ID from the query string", async () => {
    auth.getServerAuthState.mockResolvedValue({
      user: { id: "member-1" },
      hasRefreshCookie: true,
    });
    publicWork.loadPublicWork.mockResolvedValue({
      kind: "detail",
      detail: {
        id: "different-work",
        title: "Gốm làng cổ",
        canonicalSlug: "gom-lang-co",
      },
    });

    const page = await CommunityNewPage({
      searchParams: Promise.resolve({
        relatedWorkId: "forged-id",
        relatedWorkSlug: "gom-lang-co",
      }),
    });

    expect(page.props.relatedWork).toBeNull();
  });
});
