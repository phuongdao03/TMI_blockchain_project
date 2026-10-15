import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import CommunityModerationPage from "./page";

vi.mock("@/components/auth/role-gate", () => ({
  RoleGate: ({
    allowed,
    children,
    permissions,
  }: {
    allowed: string[];
    children: ReactNode;
    permissions: string[];
  }) => (
    <div data-allowed={allowed.join(",")} data-permissions={permissions.join(",")}>
      {children}
    </div>
  ),
}));
vi.mock("@/components/community/community-admin-workspace", () => ({
  CommunityAdminWorkspace: () => <div>Community admin workspace</div>,
}));

describe("CommunityModerationPage", () => {
  it("gates the workspace by moderation or management capability", () => {
    const { container } = render(<CommunityModerationPage />);

    expect(screen.getByText("Community admin workspace")).toBeDefined();
    expect(container.firstElementChild?.getAttribute("data-allowed")).toBe("SUPER_ADMIN");
    expect(container.firstElementChild?.getAttribute("data-permissions")).toBe(
      "community.moderate,community.manage",
    );
  });
});
