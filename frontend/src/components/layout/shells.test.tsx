import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const navigationState = vi.hoisted(() => ({ pathname: "/" }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
}));

vi.mock("@/components/auth/logout-button", () => ({
  LogoutButton: () => <button type="button">Đăng xuất</button>,
}));

import {
  AuthShell,
  DashboardShell,
  PublicShell,
} from "@/components/layout/shells";
import { PublicExperienceShell } from "@/components/layout/public-experience-shell";
import { AuthUserProvider } from "@/lib/auth/user-context";

describe("layout shells", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    navigationState.pathname = "/";
  });

  it("keeps preview-only journeys out of the primary public header", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(
      <PublicShell>
        <h1>Preview</h1>
      </PublicShell>,
    );

    expect(screen.getAllByRole("link", { name: "Đề cử" })).toHaveLength(2);
    expect(screen.queryByRole("link", { name: /Bình chọn/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Gửi đề cử/ })).toBeNull();
  });

  it("renders public navigation with auth entry points", () => {
    render(
      <PublicShell>
        <h1>Nền tảng chứng thư tài sản số</h1>
      </PublicShell>,
    );
    expect(screen.getByRole("banner")).toBeDefined();
    expect(
      screen.getByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeDefined();
    expect(screen.getAllByRole("link", { name: "Trang chủ" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Minh bạch" })).toHaveLength(2);
    expect(
      screen.queryByRole("complementary", {
        name: "Điều hướng công khai",
      }),
    ).toBeNull();
    expect(screen.getByRole("link", { name: "Đăng nhập" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Đăng ký" })).toBeDefined();
  });

  it("renders the auth shell with a labelled main region", () => {
    render(
      <AuthShell>
        <h1>Đăng nhập</h1>
      </AuthShell>,
    );
    expect(
      screen.getByRole("main", { name: "Tài khoản Đề cử Tinh Hoa Việt" }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Quy trình" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Chính sách" })).toBeDefined();
    expect(screen.queryByText("Bảo vệ tài khoản")).toBeNull();
    expect(
      screen.getByRole("heading", { level: 1, name: "Đăng nhập" }),
    ).toBeDefined();
  });

  it("renders applicant navigation on desktop and mobile", () => {
    render(
      <AuthUserProvider
        user={{
          id: "user-1",
          email: "owner@tmigroup.vn",
          roles: ["APPLICANT"],
          accountType: "INDIVIDUAL_APPLICANT",
        }}
      >
        <DashboardShell>
          <h1>Tổng quan</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );
    expect(
      screen.getByRole("navigation", { name: "Điều hướng bảng điều khiển" }),
    ).toBeDefined();
    expect(screen.getByText("Mở điều hướng")).toBeDefined();
    expect(screen.getAllByText("Không gian của bạn")).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Tổng quan" })).toHaveLength(2);
    expect(screen.queryByText("Việc cần làm")).toBeNull();
    expect(
      screen
        .getAllByRole("link")
        .filter((link) => link.getAttribute("href") === "/dashboard"),
    ).toHaveLength(2);
    expect(
      screen.queryByRole("link", { name: "Quản trị nội dung" }),
    ).toBeNull();
    expect(screen.queryByText("Môi trường thử nghiệm")).toBeNull();
    expect(screen.queryByText("Hệ thống xác minh sẵn sàng")).toBeNull();
  });

  it("keeps public discovery links visible for an authenticated public user", () => {
    render(
      <AuthUserProvider
        user={{
          id: "user-2",
          email: "reader@tmigroup.vn",
          roles: [],
          accountType: "PUBLIC_USER",
        }}
      >
        <DashboardShell>
          <h1>KhÃ¡m phÃ¡</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );

    const links = screen.getAllByRole("link");
    for (const href of ["/dashboard", "/search", "/works", "/map"]) {
      expect(links.some((link) => link.getAttribute("href") === href)).toBe(
        true,
      );
    }
    expect(
      links.some((link) => link.getAttribute("href") === "/dossiers"),
    ).toBe(false);
  });

  it("shows one compact workspace action instead of email and auth CTAs", () => {
    render(
      <PublicShell
        user={{
          id: "user-3",
          email: "reviewer@tmigroup.vn",
          roles: ["REVIEWER"],
          accountType: "PUBLIC_USER",
        }}
      >
        <h1>Catalog</h1>
      </PublicShell>,
    );

    expect(
      screen
        .getByRole("link", { name: "Không gian của tôi" })
        .getAttribute("href"),
    ).toBe("/reviews");
    expect(screen.queryByText("reviewer@tmigroup.vn")).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng nhập" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng ký" })).toBeNull();
  });

  it("keeps signed-in discovery pages inside the dashboard shell", () => {
    navigationState.pathname = "/search";
    render(
      <PublicExperienceShell
        user={{
          id: "user-4",
          email: "reader@tmigroup.vn",
          roles: [],
          accountType: "PUBLIC_USER",
        }}
      >
        <h1>Tìm kiếm đề cử</h1>
      </PublicExperienceShell>,
    );

    expect(
      screen.getByRole("navigation", { name: "Điều hướng bảng điều khiển" }),
    ).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Tìm kiếm đề cử" })[0]
        ?.getAttribute("aria-current"),
    ).toBe("page");
    expect(
      screen.queryByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeNull();
  });
});
