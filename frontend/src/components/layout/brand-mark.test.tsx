import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BrandMark } from "@/components/layout/brand-mark";

describe("BrandMark", () => {
  it("shows the official symbol and clear name in compact workspaces", () => {
    render(<BrandMark compact />);

    const homeLink = screen.getByRole("link", {
      name: "Đề cử và xác lập Tinh Hoa Việt",
    });
    const sources = Array.from(homeLink.querySelectorAll("img"), (logo) =>
      decodeURIComponent(logo.getAttribute("src") ?? ""),
    );

    expect(sources).toHaveLength(2);
    expect(sources[0]).toContain("/assets/brand/logo-tinh-hoa-viet.png");
    expect(sources[1]).toContain("/assets/brand/thv-wordmark-gold.png");
  });

  it("renders the approved Tinh Hoa Việt wordmark", () => {
    render(<BrandMark />);

    const homeLink = screen.getByRole("link", {
      name: "Đề cử và xác lập Tinh Hoa Việt",
    });
    const logo = homeLink.querySelector("img:first-of-type");
    const wordmark = homeLink.querySelector("img.brand-mark__wordmark-image");
    const source = logo?.getAttribute("src");

    expect(logo).not.toBeNull();
    expect(logo?.getAttribute("alt")).toBe("");
    expect(logo?.getAttribute("sizes")).toBe("(max-width: 38rem) 56px, 76px");
    expect(decodeURIComponent(source ?? "")).toContain(
      "/assets/brand/logo-tinh-hoa-viet.png",
    );
    expect(decodeURIComponent(wordmark?.getAttribute("src") ?? "")).toContain(
      "/assets/brand/thv-wordmark-gold.png",
    );
    expect(homeLink.textContent).not.toContain("Tinh Hoa Việt");
    expect(screen.queryByText(/Phát triển bởi/)).toBeNull();
  });

  it("shows the supplied seal as the single public logo", () => {
    render(<BrandMark variant="public-seal" />);

    const homeLink = screen.getByRole("link", {
      name: "Đề cử và xác lập Tinh Hoa Việt",
    });
    const logos = homeLink.querySelectorAll("img");

    expect(logos).toHaveLength(1);
    expect(decodeURIComponent(logos[0]?.getAttribute("src") ?? "")).toContain(
      "/assets/brand/logo-tinh-hoa-viet.png",
    );
  });

  it("shows the platform credit when requested", () => {
    render(<BrandMark showCredit />);

    expect(screen.getByText("Nền tảng Đề cử Tinh Hoa Việt")).toBeDefined();
  });
});
