import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BrandMark } from "@/components/layout/brand-mark";

describe("BrandMark", () => {
  it("renders the approved Tinh Hoa Việt wordmark", () => {
    render(<BrandMark />);

    const homeLink = screen.getByRole("link", {
      name: "Trung tâm Đề cử Tinh Hoa Việt",
    });
    const logo = homeLink.querySelector("img");
    const source = logo?.getAttribute("src");

    expect(logo).not.toBeNull();
    expect(logo?.getAttribute("alt")).toBe("");
    expect(decodeURIComponent(source ?? "")).toContain(
      "/assets/brand/thv-brand-wordmark.png",
    );
    expect(screen.queryByText(/Phát triển bởi/)).toBeNull();
  });

  it("adds the CNS attribution only where it is explicitly requested", () => {
    render(<BrandMark showCredit />);

    expect(
      screen.getByText("Phát triển bởi Trung tâm An ninh Công nghệ số – CNS"),
    ).toBeDefined();
  });
});
