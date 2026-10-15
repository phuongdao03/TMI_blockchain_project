import { describe, expect, it, vi } from "vitest";

const navigation = vi.hoisted(() => ({ redirect: vi.fn() }));

vi.mock("next/navigation", () => ({ redirect: navigation.redirect }));

import CommunityAliasPage from "@/app/(public)/cong-dong/page";

describe("CommunityAliasPage", () => {
  it("redirects the Vietnamese legacy path to the canonical community route", () => {
    CommunityAliasPage();

    expect(navigation.redirect).toHaveBeenCalledWith("/community");
  });
});
