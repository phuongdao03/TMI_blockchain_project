import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/featured-assets", () => ({
  FeaturedAssets: () => <div>Tài sản tiêu biểu</div>,
}));

describe("HomePage", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("uses honest preview CTAs before submissions are available", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(<HomePage />);

    expect(screen.getByText("Đề cử Tinh Hoa Việt")).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Khám phá đề cử" }).getAttribute("href"),
    ).toBe("/works");
    expect(screen.getByText("DẤU ẤN TINH HOA VIỆT")).toBeDefined();
    expect(screen.getByText("GIÁ TRỊ ĐƯỢC GÌN GIỮ VÀ LAN TỎA")).toBeDefined();
    expect(screen.queryByText("NỘI DUNG GIỚI THIỆU")).toBeNull();
    expect(screen.queryByText(/Phiên bản V1|sau V1/)).toBeNull();
    expect(screen.queryByText("Sẵn sàng xác minh")).toBeNull();
    expect(screen.queryByText("Khởi tạo hồ sơ")).toBeNull();
  });

  it("presents the premium evidence registry and primary public actions", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Nơi những giá trị Việt được giới thiệu, ghi nhận và lan tỏa.",
      }),
    ).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Khám phá đề cử" })[0]
        ?.getAttribute("href"),
    ).toBe("/works");
    expect(
      screen
        .getByRole("link", { name: "Tìm hiểu chương trình" })
        .getAttribute("href"),
    ).toBe("/process");
    expect(
      screen.getByRole("img", { name: "Hồ sơ đề cử minh họa" }),
    ).toBeDefined();
    expect(
      screen.getByRole("search", { name: "Tìm kiếm đề cử" }),
    ).toBeDefined();
  });
});
