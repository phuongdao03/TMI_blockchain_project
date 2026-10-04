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

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Suy tôn trí tuệ. Lưu truyền di sản.",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Khám phá đề cử" }).getAttribute("href"),
    ).toBe("/works");
    expect(
      screen.getByRole("img", {
        name: "Họa tiết chim Lạc màu trắng trên nền đỏ",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", {
        name: "Biểu trưng Trung tâm Xác lập Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(screen.queryByText(/Phiên bản V1|sau V1/)).toBeNull();
    expect(screen.queryByText("THV–VN–2026–0812")).toBeNull();
    expect(screen.queryByText("Khởi tạo hồ sơ")).toBeNull();
  });

  it("presents the premium evidence registry and primary public actions", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Suy tôn trí tuệ. Lưu truyền di sản.",
      }),
    ).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Khám phá đề cử" })[0]
        ?.getAttribute("href"),
    ).toBe("/works");
    expect(
      screen
        .getByRole("link", { name: "Xem văn bản thành lập" })
        .getAttribute("href"),
    ).toBe("#van-ban-thanh-lap");
    expect(
      screen.getByRole("img", {
        name: "Họa tiết mặt trống đồng với các vòng hoa văn đồng tâm",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("search", { name: "Tìm kiếm đề cử" }),
    ).toBeDefined();
    expect(
      screen.queryByText(/Bình chọn và cổng gửi đề cử sẽ được mở/i),
    ).toBeNull();
    expect(
      screen.getByText(
        "Tạo tài khoản để gửi hồ sơ, nhận phản hồi và quản lý thông tin của bạn.",
      ),
    ).toBeDefined();
  });

  it("explains the public journey with three concrete verification steps", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Xem giá trị Việt theo ba bước rõ ràng.",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { level: 3, name: "Khám phá đề cử" }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Đọc câu chuyện & hồ sơ",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Kiểm chứng thông tin",
      }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: /Tra cứu bằng xác lập/i })
        .getAttribute("href"),
    ).toBe("/verify");
    expect(
      document.querySelectorAll(".journey-workflow__icon-frame"),
    ).toHaveLength(3);
  });

  it("publishes establishment evidence and the 2026 event dossier", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { name: /Trung tâm Xác lập Tinh Hoa Việt/ }),
    ).toBeDefined();
    expect(screen.getByText("Quyết định số 55")).toBeDefined();
    expect(screen.getByText("02/01/2026")).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Xem quyết định" }).getAttribute("href"),
    ).toBe("/assets/institution/decision.pdf");
    expect(
      screen
        .getByRole("link", { name: "Tải proposal PDF" })
        .getAttribute("href"),
    ).toBe("/assets/institution/proposal-2026.pdf");
    expect(
      screen.getByRole("region", { name: "Trình xem proposal" }),
    ).toBeDefined();
    expect(screen.getByRole("status").textContent).toContain("Trang 1 / 53");
  });
});
