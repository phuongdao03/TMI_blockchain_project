import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/featured-assets", () => ({
  FeaturedAssets: () => <div>Tài sản tiêu biểu</div>,
}));

describe("HomePage", () => {
  it("presents the premium evidence registry and primary public actions", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Bằng chứng cho giá trị số, được thiết kế để kiểm chứng.",
      }),
    ).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Khởi tạo hồ sơ" })[0]
        ?.getAttribute("href"),
    ).toBe("/register");
    expect(
      screen
        .getByRole("link", { name: "Khám phá quy trình" })
        .getAttribute("href"),
    ).toBe("/process");
    expect(
      screen.getByRole("img", { name: "Sổ bằng chứng số TMI" }),
    ).toBeDefined();
    expect(
      screen.getByRole("search", { name: "Tra cứu tài sản hoặc chứng thư" }),
    ).toBeDefined();
  });
});
