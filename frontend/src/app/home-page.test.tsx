import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(public)/page";

vi.mock("@/components/public/featured-assets", () => ({
  FeaturedAssets: () => <div>Tài sản tiêu biểu</div>,
}));

describe("HomePage", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("keeps account entry links available in preview mode", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(<HomePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Suy tôn trí tuệ. Lưu truyền di sản.",
      }),
    ).toBeDefined();
    const hero = document.querySelector(".registry-hero");
    expect(hero?.querySelector('a[href="/register"]')?.textContent).toContain(
      "Đăng ký",
    );
    expect(hero?.querySelector('a[href="/login"]')?.textContent).toContain(
      "Đăng nhập",
    );
    expect(hero?.querySelector('a[href="/works"]')?.textContent).toContain(
      "Khám phá đề cử",
    );
    expect(hero?.querySelector('form[action="/works"]')).not.toBeNull();
    expect(
      hero?.querySelector(".registry-hero__copy--desktop")?.textContent,
    ).toContain("đối chiếu thông tin được công bố");
    expect(hero?.querySelector(".registry-hero__mobile-seal img")).toBeNull();
    const missionLead = document.querySelector(".mission-section__lead");
    const missionSeal = missionLead?.nextElementSibling;
    expect(missionSeal?.classList.contains("mission-section__seal")).toBe(true);
    expect(missionSeal?.querySelector("img")).not.toBeNull();
    expect(
      missionSeal?.nextElementSibling?.classList.contains(
        "mission-section__invitation",
      ),
    ).toBe(true);
    expect(document.querySelectorAll(".registry-heritage img")).toHaveLength(1);
    expect(document.querySelector(".registry-heritage__outline")).toBeNull();
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
    const hero = document.querySelector(".registry-hero");
    expect(hero?.querySelector('a[href="/register"]')).not.toBeNull();
    expect(hero?.querySelector('a[href="/login"]')).not.toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Xem văn bản thành lập" })
        .getAttribute("href"),
    ).toBe("#van-ban-thanh-lap");
    expect(
      screen.getByRole("search", { name: "Tìm kiếm đề cử" }),
    ).toBeDefined();
    expect(
      document.querySelector(".registry-hero [role='search']"),
    ).not.toBeNull();
    expect(
      document.querySelector(".home-featured [role='search']"),
    ).not.toBeNull();
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

  it("keeps the original introduction, institution, process and featured order", () => {
    render(<HomePage />);
    const sections = [...document.querySelectorAll(".public-home > section")];
    const position = (className: string) =>
      sections.findIndex((section) => section.classList.contains(className));

    for (const className of [
      "mission-section",
      "institution-section",
      "home-journey",
      "home-audiences",
      "home-featured",
    ]) {
      expect(position(className)).toBeGreaterThan(0);
    }

    expect(position("mission-section")).toBeLessThan(
      position("institution-section"),
    );
    expect(position("institution-section")).toBeLessThan(
      position("home-journey"),
    );
    expect(position("home-journey")).toBeLessThan(position("home-audiences"));
    expect(position("home-audiences")).toBeLessThan(position("home-featured"));
  });

  it("publishes establishment evidence and the 2026 event dossier", () => {
    render(<HomePage />);

    expect(
      document.querySelector(".registry-hero__provenance")?.textContent,
    ).toContain("Quyết định số 55 ngày 02/01/2026");
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
    expect(screen.getByText("Đang chuẩn bị trình đọc tài liệu…")).toBeDefined();
  });
});
