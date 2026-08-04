import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  AuthShell,
  DashboardShell,
  PublicShell,
} from "@/components/layout/shells";
import { AuthUserProvider } from "@/lib/auth/user-context";

describe("layout shells", () => {
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
    expect(
      screen.getAllByRole("link", { name: "Bình chọn cộng đồng" }),
    ).toHaveLength(2);
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
    expect(screen.getByRole("main", { name: "Tài khoản TMI" })).toBeDefined();
    expect(screen.getByText("Bảo chứng bởi blockchain")).toBeDefined();
    expect(screen.getByText("Mã hóa AES-256")).toBeDefined();
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
    expect(
      screen.getAllByRole("link", { name: "Tổng quan hồ sơ" }),
    ).toHaveLength(2);
    expect(
      screen.queryByRole("link", { name: "Quản trị nội dung" }),
    ).toBeNull();
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
    for (const href of ["/dashboard", "/tim-kiem", "/thu-vien", "/ban-do"]) {
      expect(links.some((link) => link.getAttribute("href") === href)).toBe(true);
    }
    expect(links.some((link) => link.getAttribute("href") === "/ho-so")).toBe(false);
  });
});
