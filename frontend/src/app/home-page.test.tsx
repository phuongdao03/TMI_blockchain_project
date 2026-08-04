import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/featured-assets", () => ({
  FeaturedAssets: () => <div>Tài sản tiêu biểu</div>,
}));

describe("HomePage", () => {
  it("communicates the premium verification proposition and next action", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Bằng chứng cho giá trị số, được thiết kế để kiểm chứng.",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", {
        name: "Sổ bằng chứng số TMI",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Khởi tạo hồ sơ" }).getAttribute("href"),
    ).toBe("/register");
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Một quy trình. Mỗi bước đều có bằng chứng.",
      }),
    ).toBeDefined();
  });
});
