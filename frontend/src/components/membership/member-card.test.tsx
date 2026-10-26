import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MemberCard } from "./member-card";
import { membershipTierPalette } from "./membership-tier-palette";

describe("membership cards", () => {
  it.each([
    ["MEMBER", "Đồng"],
    ["SILVER", "Bạc"],
    ["COMPANION", "Vàng"],
    ["PRESTIGE", "Kim cương"],
  ] as const)(
    "renders the %s identity without loyalty points",
    (tier, label) => {
      render(
        <MemberCard
          name="Đào Nguyễn Phương"
          membership={{
            tier,
            memberNumber: "THV-123456789ABC",
            status: tier === "MEMBER" ? "FREE" : "ACTIVE",
            expiresAt: null,
          }}
        />,
      );
      const card = screen.getByRole("article", {
        name: `Thẻ ${label} của Đào Nguyễn Phương`,
      });
      expect(card).toBeDefined();
      expect(
        (card as HTMLElement).style.getPropertyValue("--membership-accent"),
      ).toBe(membershipTierPalette[tier].accent);
      expect(screen.getByRole("heading", { name: label })).toBeDefined();
      expect(screen.getByText("THV-123456789ABC")).toBeDefined();
      expect(
        screen.queryByText(/tổng điểm|đơn hàng|affiliate|tổng hoá đơn/i),
      ).toBeNull();
    },
  );
});
