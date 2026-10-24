import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CommunityUserIdentity } from "./community-user-identity";

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
    expect(screen.getByLabelText("Hạng thẻ Bạc")).toBeDefined();
    const frame = container.querySelector<HTMLImageElement>('img[alt=""]');
    expect(frame).not.toBeNull();
    expect(decodeURIComponent(frame?.getAttribute("src") ?? "")).toContain(
      "/assets/membership/avatar-frames/silver.png",
    );
  });
});
