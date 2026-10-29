import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MembershipAvatar } from "./membership-avatar";

describe("MembershipAvatar", () => {
  it.each([
    ["MEMBER", "bronze"],
    ["SILVER", "silver"],
    ["COMPANION", "gold"],
    ["PRESTIGE", "diamond"],
  ] as const)(
    "preserves the actual %s frame on compact header avatars",
    (tier, frame) => {
      render(
        <MembershipAvatar displayName="Lan Nguyễn" size={28} tier={tier} />,
      );
      const image = [...document.querySelectorAll("img")].find((element) =>
        decodeURIComponent(element.getAttribute("src") ?? "").includes(
          `/avatar-frames/${frame}.png`,
        ),
      );
      expect(image).toBeTruthy();
    },
  );
  it.each([
    ["MEMBER", "bronze"],
    ["SILVER", "silver"],
    ["COMPANION", "gold"],
    ["PRESTIGE", "diamond"],
  ] as const)("shows the %s frame for %s membership", (tier, frame) => {
    render(<MembershipAvatar displayName="Lan Nguyễn" size={64} tier={tier} />);

    expect(
      screen.getByRole("img", { name: "Ảnh đại diện của Lan Nguyễn" }),
    ).toBeTruthy();
    const framePath = `/assets/membership/avatar-frames/${frame}.png`;
    const frameImage = [...document.querySelectorAll("img")].find((image) =>
      decodeURIComponent(image.getAttribute("src") ?? "").includes(framePath),
    );
    expect(frameImage).toBeTruthy();
    expect(frameImage?.getAttribute("alt")).toBe("");
  });

  it("keeps the avatar image and frame at the requested size", () => {
    render(
      <MembershipAvatar
        displayName="Lan Nguyễn"
        size={80}
        src="/avatar.png"
        tier="PRESTIGE"
      />,
    );

    const avatar = screen.getByRole("img", {
      name: "Ảnh đại diện của Lan Nguyễn",
    });
    expect(avatar.parentElement?.style.height).toBe("80px");
    expect(avatar.parentElement?.style.width).toBe("80px");
  });
});
