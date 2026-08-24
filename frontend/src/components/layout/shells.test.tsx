import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

    expect(screen.getAllByRole("link", { name: "Đề cử" })).toHaveLength(1);
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
    expect(screen.getAllByRole("link", { name: "Trang chủ" })).toHaveLength(1);
    expect(screen.getAllByRole("link", { name: "Minh bạch" })).toHaveLength(1);
    expect(
      screen.queryByRole("complementary", {
        name: "Điều hướng công khai",
      }),
    ).toBeNull();
    const loginLink = screen.getByRole("link", { name: "Đăng nhập" });
    const registerLink = screen.getByRole("link", { name: "Đăng ký" });
    expect(loginLink.classList.contains("public-header__auth-link")).toBe(true);
    expect(registerLink.classList.contains("public-header__auth-link")).toBe(
      true,
    );
    expect(registerLink.classList.contains("button")).toBe(false);
  });

  it("uses the official seal and wordmark together in the public header", () => {
    render(
      <PublicShell>
        <h1>Trang chủ</h1>
      </PublicShell>,
    );

    const brandLink = within(screen.getByRole("banner")).getByRole("link", {
      name: "Trung tâm Đề cử Tinh Hoa Việt",
    });
    const headerLogos = Array.from(brandLink.querySelectorAll("img"));
    const sources = headerLogos.map((logo) =>
      decodeURIComponent(logo.getAttribute("src") ?? ""),
    );

    expect(headerLogos).toHaveLength(2);
    expect(sources[0]).toContain("/assets/brand/thv-public-header-seal.png");
    expect(sources[1]).toContain(
      "/assets/brand/thv-public-header-wordmark.png",
    );
  });

  it("keeps public and auth footers limited to terms and privacy links", () => {
    render(
      <PublicShell>
        <h1>Nền tảng chứng thư tài sản số</h1>
      </PublicShell>,
    );

    const footerNavigation = screen.getByRole("navigation", {
      name: "Liên kết cuối trang",
    });
    expect(
      within(footerNavigation)
        .getByRole("link", { name: "Điều khoản sử dụng" })
        .getAttribute("href"),
    ).toBe("/policies");
    expect(
      within(footerNavigation)
        .getByRole("link", { name: "Chính sách quyền riêng tư" })
        .getAttribute("href"),
    ).toBe("/policies#privacy");
    expect(within(footerNavigation).getAllByRole("link")).toHaveLength(2);
    expect(within(footerNavigation).queryByText("Khám phá đề cử")).toBeNull();
    expect(
      within(footerNavigation).queryByText(
        "Phát triển bởi Trung tâm an ninh công nghệ số - CNS",
      ),
    ).toBeNull();

    const publicFooter = screen.getByRole("contentinfo");
    expect(
      within(publicFooter).getByRole("link", {
        name: "Trung tâm Đề cử Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(
      within(publicFooter).getByText(
        "Phát triển bởi Trung tâm An ninh Công nghệ số – CNS",
      ),
    ).toBeDefined();
  });

  it("opens mobile navigation as a viewport drawer and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(
      <PublicShell>
        <h1>Trang chủ</h1>
      </PublicShell>,
    );

    const trigger = screen.getByRole("button", { name: /menu/i });
    await user.click(trigger);

    const navigation = screen
      .getAllByRole("navigation")
      .find((element) => element.classList.contains("public-mobile-nav"));
    expect(navigation).toBeDefined();
    if (!navigation) throw new Error("Mobile navigation was not rendered");
    expect(
      navigation.parentElement?.classList.contains("public-mobile-drawer"),
    ).toBe(true);
    const homeLink = within(navigation).getByRole("link", { name: /trang/i });
    await waitFor(() => expect(document.activeElement).toBe(homeLink));

    await user.click(trigger);
    expect(
      screen
        .queryAllByRole("navigation")
        .find((element) => element.classList.contains("public-mobile-nav")),
    ).toBeUndefined();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("renders the auth shell with a labelled main region", () => {
    render(
      <AuthShell>
        <h1>Đăng nhập</h1>
      </AuthShell>,
    );
    expect(
      screen.getByRole("main", { name: "Khu vực tài khoản" }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Điều khoản sử dụng" }),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Chính sách quyền riêng tư" }),
    ).toBeDefined();
    expect(screen.queryByText("Bảo vệ tài khoản")).toBeNull();
    expect(
      screen.getByRole("heading", { level: 1, name: "Đăng nhập" }),
    ).toBeDefined();
    const header = screen.getByRole("banner");
    expect(header.querySelector(".auth-header__identity")).not.toBeNull();
    expect(
      within(header).queryByRole("link", { name: "Đăng nhập" }),
    ).toBeNull();
    expect(within(header).queryByRole("link", { name: "Đăng ký" })).toBeNull();
  });

  it("renders applicant navigation on desktop and mobile", () => {
    render(
      <AuthUserProvider
        user={{
          id: "user-1",
          email: "owner@tmigroup.vn",
          roles: ["USER"],
          accountType: "INDIVIDUAL_APPLICANT",
        }}
      >
        <DashboardShell>
          <h1>Tổng quan</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );
    expect(
      screen.getByRole("navigation", { name: "Điều hướng" }),
    ).toBeDefined();
    expect(screen.queryByText("Mở điều hướng")).toBeNull();
    expect(screen.getByText("Khám phá")).toBeDefined();
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
          roles: ["MODERATOR"],
          accountType: "PUBLIC_USER",
        }}
      >
        <h1>Catalog</h1>
      </PublicShell>,
    );

    expect(
      screen
        .getByRole("link", { name: "Khu vực thẩm định" })
        .getAttribute("href"),
    ).toBe("/reviews");
    expect(screen.queryByText("reviewer@tmigroup.vn")).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng nhập" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng ký" })).toBeNull();
  });

  it("keeps a regular user in their personal dashboard instead of advertising internal workspaces", () => {
    render(
      <PublicShell
        user={{
          id: "user-public",
          email: "reader@tmigroup.vn",
          roles: [],
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
    ).toBe("/dashboard");
    expect(screen.queryByRole("link", { name: /Quản trị nội bộ/i })).toBeNull();
  });

  it("uses the current role context instead of a generic workspace title", () => {
    navigationState.pathname = "/admin/content";
    render(
      <AuthUserProvider
        user={{
          id: "user-content-admin",
          email: "content@tmigroup.vn",
          roles: ["SUPER_ADMIN"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <p>Content administration</p>
        </DashboardShell>
      </AuthUserProvider>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Quản trị nội dung" }),
    ).toBeDefined();
  });

  it("keeps signed-in discovery pages inside the public shell", () => {
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
      screen.getByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Không gian của tôi" })
        .getAttribute("href"),
    ).toBe("/dashboard");
  });
});
