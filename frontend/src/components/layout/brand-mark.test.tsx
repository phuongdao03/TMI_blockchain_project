import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BrandMark } from "@/components/layout/brand-mark";

describe("BrandMark", () => {
  it("renders the official TMI Group logo from the brand asset directory", () => {
    render(<BrandMark />);

    const logo = screen.getByRole("img", { name: "TMI Group" });
    const source = logo.getAttribute("src");

    expect(source).not.toBeNull();
    expect(decodeURIComponent(source ?? "")).toContain(
      "/assets/brand/tmi-group-logo.png",
    );
  });
});
