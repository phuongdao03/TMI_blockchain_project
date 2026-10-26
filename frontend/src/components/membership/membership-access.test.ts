import { describe, expect, it } from "vitest";

import { canUsePersonalMembership } from "./membership-access";

describe("personal membership access", () => {
  it("excludes super admins and membership managers", () => {
    expect(
      canUsePersonalMembership({
        roles: ["SUPER_ADMIN"],
      }),
    ).toBe(false);
    expect(
      canUsePersonalMembership({
        roles: ["MODERATOR"],
        permissions: ["memberships.manage"],
      }),
    ).toBe(false);
  });

  it("keeps personal membership for other authenticated roles", () => {
    expect(
      canUsePersonalMembership({
        roles: ["USER"],
        permissions: ["community.moderate"],
      }),
    ).toBe(true);
  });
});
