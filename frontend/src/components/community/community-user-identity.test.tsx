import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CommunityMembershipBadge,
  CommunityUserIdentity,
  getAuthenticatedCommunityIdentity,
} from "./community-user-identity";
import { membershipTierPalette } from "@/components/membership/membership-tier-palette";

describe("community membership identity", () => {
  it("uses the Silver frame and label for Silver community members", () => {
    const { container } = render(
      <CommunityUserIdentity
        size={40}
        user={{
          id: "member-1",
          username: "lan-nguyen",
          displayName: "Lan Nguyễn",
          avatarUrl: null,
          membershipTier: "SILVER",
        }}
      />,
    );
    const badge = screen.getByLabelText("Hạng thẻ Bạc") as HTMLElement;
    expect(badge).toBeDefined();
    expect(badge.style.borderColor).toBe(membershipTierPalette.SILVER.border);
    expect(badge.style.backgroundColor).toBe(
      membershipTierPalette.SILVER.surface,
    );
    expect(badge.style.color).toBe(membershipTierPalette.SILVER.ink);
    const frame = container.querySelector<HTMLImageElement>('img[alt=""]');
    expect(frame).not.toBeNull();
    expect(decodeURIComponent(frame?.getAttribute("src") ?? "")).toContain(
      "/assets/membership/avatar-frames/silver.png",
    );
  });

  it("keeps admin role identity without assigning a membership rank or frame", () => {
    const { container } = render(
      <CommunityUserIdentity
        user={{
          id: "admin-1",
          username: "admin",
          displayName: "Quản trị viên THV",
          avatarUrl: null,
          isAdmin: true,
          roleLabel: "Quản trị viên",
          membershipTier: "MEMBER",
        }}
      />,
    );

    expect(screen.getByText("Quản trị viên")).toBeDefined();
    expect(screen.queryByLabelText(/Hạng thẻ/)).toBeNull();
    expect(container.querySelector('img[src*="avatar-frames"]')).toBeNull();
  });

  it("keeps a membership manager role label separate from member rank", () => {
    expect(
      getAuthenticatedCommunityIdentity({
        roles: ["MODERATOR"],
        permissions: ["memberships.manage"],
      }),
    ).toMatchObject({ isAdmin: false, roleLabel: "Quản lý hội viên" });
  });

  it("uses the shared tier palette and never assigns a rank badge to an admin", () => {
    const { container } = render(<CommunityMembershipBadge tier="MEMBER" />);
    const badge = container.firstElementChild as HTMLElement;
    expect(badge.style.borderColor).toBe(membershipTierPalette.MEMBER.border);
    expect(badge.style.backgroundColor).toBe(
      membershipTierPalette.MEMBER.surface,
    );
    expect(badge.style.color).toBe(membershipTierPalette.MEMBER.ink);

    const { container: adminContainer } = render(
      <CommunityMembershipBadge tier="MEMBER" isMembershipStaff />,
    );
    expect(adminContainer.firstElementChild).toBeNull();
  });

  it("does not show a personal rank for membership managers", () => {
    const { container } = render(
      <CommunityUserIdentity
        user={{
          id: "manager-1",
          username: "manager",
          displayName: "Quản lý hội viên",
          avatarUrl: null,
          isAdmin: false,
          roleLabel: "Quản lý hội viên",
          membershipTier: "PRESTIGE",
        }}
      />,
    );

    expect(screen.getByText("Quản lý hội viên")).toBeDefined();
    expect(screen.queryByLabelText(/Hạng thẻ/)).toBeNull();
    expect(container.querySelector('img[src*="avatar-frames"]')).toBeNull();
  });
});
