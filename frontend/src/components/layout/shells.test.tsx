import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  render as testingLibraryRender,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const navigationState = vi.hoisted(() => ({ pathname: "/", search: "" }));

vi.mock("next/navigation", () => ({
  usePathname: () => navigationState.pathname,
  useSearchParams: () => new URLSearchParams(navigationState.search),
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
import { useAuthUser } from "@/lib/auth/user-context";

function render(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return testingLibraryRender(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("layout shells", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    navigationState.pathname = "/";
    navigationState.search = "";
  });

  it("keeps preview-only journeys out of the primary public header", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(
      <PublicShell>
        <h1>Preview</h1>
      </PublicShell>,
    );

    expect(
      screen.getAllByRole("link", { name: "Danh sách đề cử" }),
    ).toHaveLength(1);
    expect(screen.queryByRole("link", { name: /Bình chọn/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Gửi đề cử/ })).toBeNull();
  });

  it("renders public navigation with auth entry points", () => {
    navigationState.pathname = "/works/published-work";
    navigationState.search = "category=history";
    render(
      <PublicShell>
        <h1>Nền tảng bằng xác lập tài sản số</h1>
      </PublicShell>,
    );
    expect(screen.getByRole("banner")).toBeDefined();
    expect(
      screen.getByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeDefined();
    expect(screen.getAllByRole("link", { name: "Trang chủ" })).toHaveLength(2);
    expect(
      screen.getAllByRole("link", { name: "Tra cứu bằng xác lập" }),
    ).toHaveLength(1);
    expect(
      within(screen.getByRole("banner"))
        .getByRole("link", { name: "Cộng đồng" })
        .getAttribute("href"),
    ).toBe("/community");
    expect(screen.getAllByRole("link", { name: "Hướng dẫn" })).toHaveLength(1);
    expect(
      screen.queryByRole("complementary", {
        name: "Điều hướng công khai",
      }),
    ).toBeNull();
    const header = screen.getByRole("banner");
    const loginLink = within(header).getByRole("link", { name: "Đăng nhập" });
    const registerLink = within(header).getByRole("link", { name: "Đăng ký" });
    expect(loginLink.getAttribute("href")).toBe(
      "/login?next=%2Fworks%2Fpublished-work%3Fcategory%3Dhistory",
    );
    expect(registerLink.getAttribute("href")).toBe(
      "/register?next=%2Fworks%2Fpublished-work%3Fcategory%3Dhistory",
    );
    expect(
      screen
        .getByRole("navigation", { name: "Điều hướng di động" })
        .querySelector(
          'a[href="/login?next=%2Fworks%2Fpublished-work%3Fcategory%3Dhistory"]',
        ),
    ).not.toBeNull();
    expect(loginLink.classList.contains("public-header__auth-link")).toBe(true);
    expect(registerLink.classList.contains("public-header__auth-link")).toBe(
      true,
    );
    expect(loginLink.classList.contains("public-header__login")).toBe(true);
    expect(registerLink.classList.contains("public-header__register")).toBe(
      true,
    );
    expect(loginLink.querySelector("svg")).not.toBeNull();
    expect(registerLink.querySelector("svg")).not.toBeNull();
    expect(registerLink.classList.contains("button")).toBe(false);
    expect(
      screen.queryByRole("navigation", { name: "Truy cập tài khoản" }),
    ).toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Danh sách đề cử" })
        .getAttribute("aria-current"),
    ).toBe("page");
  });

  it("shares the verified server user with public community content", () => {
    function AuthProbe() {
      const user = useAuthUser();
      return <p>{user?.id ?? "anonymous"}</p>;
    }

    render(
      <PublicExperienceShell
        user={{
          id: "community-user",
          email: "member@example.com",
          roles: ["USER"],
          permissions: [],
          isEmployee: false,
          accountType: "PUBLIC_USER",
        }}
      >
        <AuthProbe />
      </PublicExperienceShell>,
    );

    expect(screen.getByText("community-user")).toBeDefined();
  });

  it("shows the complete brand beside the supplied seal in the public header", () => {
    render(
      <PublicShell>
        <h1>Trang chủ</h1>
      </PublicShell>,
    );

    const brandLink = within(screen.getByRole("banner")).getByRole("link", {
      name: "Đề cử và xác lập Tinh Hoa Việt",
    });
    const headerLogos = Array.from(brandLink.querySelectorAll("img"));
    const sources = headerLogos.map((logo) =>
      decodeURIComponent(logo.getAttribute("src") ?? ""),
    );

    expect(headerLogos).toHaveLength(2);
    expect(sources[0]).toContain("/assets/brand/logo-tinh-hoa-viet.png");
    expect(sources[1]).toContain("/assets/brand/thv-wordmark-gold.png");
    expect(brandLink.textContent).toBe("");
  });

  it("keeps public and auth footers limited to terms and privacy links", () => {
    render(
      <PublicShell>
        <h1>Nền tảng bằng xác lập tài sản số</h1>
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
      within(footerNavigation).queryByText(/Đơn vị phát triển/),
    ).toBeNull();

    const publicFooter = screen.getByRole("contentinfo");
    expect(publicFooter.querySelector(".public-footer__inner")).not.toBeNull();
    const footerBrand = within(publicFooter).getByRole("link", {
      name: "Đề cử và xác lập Tinh Hoa Việt",
    });
    const footerLogos = footerBrand.querySelectorAll("img");
    expect(footerLogos).toHaveLength(1);
    expect(
      decodeURIComponent(footerLogos[0]?.getAttribute("src") ?? ""),
    ).toContain("/assets/brand/logo-tinh-hoa-viet.png");
    expect(
      within(publicFooter).getByText("Trung tâm An ninh Công nghệ số - CNS"),
    ).toBeDefined();
    expect(
      within(publicFooter).getByText(/Viện Những Vấn đề Phát triển/),
    ).toBeDefined();
    expect(
      within(publicFooter).getByRole("img", {
        name: "Viện Những Vấn đề Phát triển (VIDS)",
      }),
    ).toBeDefined();
    expect(
      within(publicFooter).getByRole("img", { name: "Báo chí Online" }),
    ).toBeDefined();
    expect(
      within(publicFooter).queryAllByRole("img", {
        name: "Trung tâm Xác lập Tinh Hoa Việt",
      }),
    ).toHaveLength(0);
    expect(within(publicFooter).getByText("Đơn vị đồng hành")).toBeDefined();
    expect(
      within(publicFooter)
        .getByRole("link", { name: "0834.11.22.88" })
        .getAttribute("href"),
    ).toBe("tel:0834112288");
    expect(
      within(publicFooter)
        .getByRole("link", { name: "0989.55.3535" })
        .getAttribute("href"),
    ).toBe("tel:0989553535");
    expect(
      within(publicFooter)
        .getByRole("link", { name: "decu@tinhhoaviet.org.vn" })
        .getAttribute("href"),
    ).toBe("mailto:decu@tinhhoaviet.org.vn");
  });

  it("opens mobile navigation as a viewport drawer and restores trigger focus", async () => {
    const user = userEvent.setup();
    render(
      <PublicShell>
        <h1>Trang chủ</h1>
      </PublicShell>,
    );

    const trigger = screen.getByRole("button", { name: /menu/i });
    const originalOverflow = document.body.style.overflow;
    await user.click(trigger);
    expect(document.body.style.overflow).toBe(originalOverflow);
    expect(screen.getAllByRole("button", { name: "Đóng menu" })).toHaveLength(
      1,
    );

    const navigation = screen
      .getAllByRole("navigation")
      .find((element) => element.classList.contains("public-mobile-nav"));
    expect(navigation).toBeDefined();
    if (!navigation) throw new Error("Mobile navigation was not rendered");
    expect(
      navigation.parentElement?.classList.contains("public-mobile-drawer"),
    ).toBe(true);
    expect(
      within(navigation).getByRole("group", { name: "Chọn giao diện" }),
    ).toBeDefined();
    expect(
      within(navigation).getByRole("link", { name: "Đăng nhập" }),
    ).toBeDefined();
    expect(
      within(navigation).getByRole("link", { name: "Đăng ký" }),
    ).toBeDefined();
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

  it("traps keyboard focus inside the public mobile drawer", async () => {
    const user = userEvent.setup();
    render(
      <PublicShell>
        <h1>Trang chủ</h1>
      </PublicShell>,
    );

    await user.click(screen.getByRole("button", { name: "Mở menu" }));
    const navigation = screen.getByRole("navigation", {
      name: "Menu công khai",
    });
    const links = within(navigation).getAllByRole("link");

    await waitFor(() => expect(document.activeElement).toBe(links[0]));
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(document.activeElement).toBe(links.at(-1));

    await user.keyboard("{Tab}");
    expect(document.activeElement).toBe(links[0]);
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
    const footer = screen.getByRole("contentinfo");
    expect(
      within(footer).getByText(/Trung tâm An ninh Công nghệ số/),
    ).toBeDefined();
  });

  it("renders personal navigation with the shared mobile destinations", () => {
    render(
      <AuthUserProvider
        user={{
          id: "user-1",
          email: "owner@cnsgroup.vn",
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
    expect(screen.getAllByRole("link", { name: "Tổng quan" })).toHaveLength(1);
    expect(screen.queryByText("Việc cần làm")).toBeNull();
    const mobileNavigation = screen.getByRole("navigation", {
      name: "Điều hướng di động",
    });
    expect(within(mobileNavigation).getAllByRole("link")).toHaveLength(4);
    for (const href of ["/", "/works", "/community", "/workspace"]) {
      expect(
        mobileNavigation.querySelector(`a[href="${href}"]`),
      ).not.toBeNull();
    }
    expect(mobileNavigation.querySelector('a[href="/dashboard"]')).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Quản trị nội dung" }),
    ).toBeNull();
    expect(screen.queryByText("Môi trường thử nghiệm")).toBeNull();
    expect(screen.queryByText("Hệ thống xác minh sẵn sàng")).toBeNull();
  });

  it("opens the complete workspace navigation on mobile and restores focus", async () => {
    const user = userEvent.setup();
    render(
      <AuthUserProvider
        user={{
          id: "user-mobile",
          email: "owner@example.vn",
          roles: ["USER"],
          accountType: "INDIVIDUAL_APPLICANT",
        }}
      >
        <DashboardShell>
          <p>Workspace</p>
        </DashboardShell>
      </AuthUserProvider>,
    );

    const trigger = screen.getByRole("button", {
      name: "Mở điều hướng workspace",
    });
    await user.click(trigger);

    const drawer = screen.getByRole("dialog", {
      name: "Điều hướng workspace",
    });
    expect(
      within(drawer).getByRole("link", { name: "Hồ sơ của tôi" }),
    ).toBeDefined();
    expect(
      within(drawer).getByRole("link", { name: "Hoạt động gần đây" }),
    ).toBeDefined();
    expect(
      within(drawer).getByRole("link", { name: "Hướng dẫn" }),
    ).toBeDefined();

    const closeButton = within(drawer).getByRole("button", {
      name: "Đóng điều hướng workspace",
    });
    closeButton.focus();
    await user.keyboard("{Shift>}{Tab}{/Shift}");
    expect(document.activeElement).toBe(
      within(drawer).getByRole("button", { name: "Đăng xuất" }),
    );

    await user.keyboard("{Escape}");
    expect(
      screen.queryByRole("dialog", { name: "Điều hướng workspace" }),
    ).toBeNull();
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("opens the workspace drawer from the shared mobile More destination", async () => {
    const user = userEvent.setup();
    render(
      <AuthUserProvider
        user={{
          id: "user-mobile-quick-menu",
          email: "owner@example.vn",
          roles: ["USER"],
          accountType: "INDIVIDUAL_APPLICANT",
        }}
      >
        <DashboardShell>
          <p>Workspace</p>
        </DashboardShell>
      </AuthUserProvider>,
    );

    const quickNavigation = screen.getByRole("navigation", {
      name: "Điều hướng di động",
    });
    expect(within(quickNavigation).getAllByRole("link")).toHaveLength(4);
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Cá nhân" })
        .getAttribute("href"),
    ).toBe("/workspace");
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Cộng đồng" })
        .getAttribute("href"),
    ).toBe("/community");

    const moreButton = within(quickNavigation).getByRole("button", {
      name: "Mở thêm mục điều hướng",
    });
    await user.click(moreButton);

    expect(
      screen.getByRole("dialog", { name: "Điều hướng workspace" }),
    ).toBeDefined();
    const drawer = screen.getByRole("dialog", {
      name: "Điều hướng workspace",
    });
    expect(
      within(drawer).getByRole("group", { name: "Chọn giao diện" }),
    ).toBeDefined();
    expect(
      within(drawer).getByRole("button", { name: "Đăng xuất" }),
    ).toBeDefined();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(document.activeElement).toBe(moreButton));
  });

  it("keeps admin modules out of the mobile bar and in the admin drawer", async () => {
    navigationState.pathname = "/admin";
    const user = userEvent.setup();
    render(
      <AuthUserProvider
        user={{
          id: "super-admin-mobile",
          email: "admin@example.vn",
          roles: ["SUPER_ADMIN"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <p>Administration</p>
        </DashboardShell>
      </AuthUserProvider>,
    );

    expect(
      screen.queryByRole("navigation", { name: "Điều hướng di động" }),
    ).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Mở điều hướng quản trị" }),
    );
    const drawer = screen.getByRole("dialog", { name: "Điều hướng quản trị" });
    expect(
      within(drawer)
        .getByRole("link", { name: "Không gian cá nhân" })
        .getAttribute("href"),
    ).toBe("/workspace");
    expect(
      within(drawer)
        .getByRole("link", { name: "Website" })
        .getAttribute("href"),
    ).toBe("/");
    expect(
      within(drawer)
        .getByRole("link", { name: "Cộng đồng" })
        .getAttribute("href"),
    ).toBe("/community");
    expect(
      within(drawer)
        .getByRole("link", { name: "Ghi nhận hồ sơ" })
        .getAttribute("href"),
    ).toBe("/admin/registry");
  });

  it("opens the internal guide from the super admin workspace", () => {
    navigationState.pathname = "/admin";
    render(
      <AuthUserProvider
        user={{
          id: "super-admin-guide",
          email: "admin@example.vn",
          roles: ["SUPER_ADMIN"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <p>Workspace</p>
        </DashboardShell>
      </AuthUserProvider>,
    );

    const guideLinks = screen.getAllByRole("link", { name: "Hướng dẫn" });
    expect(
      guideLinks.some((link) => link.getAttribute("href") === "/admin/guide"),
    ).toBe(true);
    expect(
      guideLinks.some((link) => link.getAttribute("href") === "/guide"),
    ).toBe(false);
    expect(screen.queryByRole("link", { name: "Phiên xét duyệt" })).toBeNull();
  });

  it("keeps public discovery links visible for an authenticated public user", () => {
    render(
      <AuthUserProvider
        user={{
          id: "user-2",
          email: "reader@cnsgroup.vn",
          roles: [],
          accountType: "PUBLIC_USER",
        }}
      >
        <DashboardShell>
          <h1>Khám phá</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );

    const links = screen.getAllByRole("link");
    for (const href of ["/workspace", "/works"]) {
      expect(links.some((link) => link.getAttribute("href") === href)).toBe(
        true,
      );
    }
    expect(links.some((link) => link.getAttribute("href") === "/map")).toBe(
      false,
    );
    expect(
      links.some((link) => link.getAttribute("href") === "/dossiers"),
    ).toBe(false);
  });

  it("keeps the public page and exposes permission backed admin access in the account menu", async () => {
    const user = userEvent.setup();
    render(
      <AuthUserProvider
        user={{
          id: "user-3",
          email: "reviewer@cnsgroup.vn",
          roles: ["MODERATOR"],
          permissions: ["community.moderate"],
          accountType: "PUBLIC_USER",
        }}
      >
        <PublicShell>
          <h1>Catalog</h1>
        </PublicShell>
      </AuthUserProvider>,
    );

    expect(screen.getByRole("heading", { name: "Catalog" })).toBeDefined();
    expect(screen.getByText("Thành viên")).toBeDefined();
    expect(screen.getByText("Thẩm định viên")).toBeDefined();
    expect(screen.queryByText("reviewer@cnsgroup.vn")).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng nhập" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Đăng ký" })).toBeNull();
    await user.click(screen.getByLabelText("Mở menu tài khoản"));
    const accountMenu = screen.getByRole("navigation", {
      name: "Menu tài khoản",
    });
    expect(
      within(accountMenu)
        .getByRole("link", { name: "Khu vực quản trị" })
        .getAttribute("href"),
    ).toBe("/admin/community");
    expect(
      within(accountMenu)
        .getByRole("link", { name: "Không gian cá nhân" })
        .getAttribute("href"),
    ).toBe("/workspace");
  });

  it("does not advertise Super Admin council work to a moderator", () => {
    render(
      <AuthUserProvider
        user={{
          id: "reviewer-navigation",
          email: "reviewer@cnsgroup.vn",
          roles: ["MODERATOR"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <h1>Hàng đợi thẩm định</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );

    expect(screen.queryByRole("link", { name: "Phiên xét duyệt" })).toBeNull();
    expect(
      screen.getAllByRole("link", { name: "Công việc được giao" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("link", { name: "Đối chiếu nội dung" }),
    ).toBeNull();
  });

  it("shows only permission-backed operations in a scoped admin area", () => {
    navigationState.pathname = "/admin/payments";
    render(
      <AuthUserProvider
        user={{
          id: "finance-navigation",
          email: "finance@cnsgroup.vn",
          roles: ["USER"],
          permissions: ["payments.read", "payments.reconcile"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <h1>Thu phí</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );

    expect(
      screen.getAllByRole("link", { name: "Thu phí" }).length,
    ).toBeGreaterThan(0);
    expect(screen.queryByRole("link", { name: "Người dùng" })).toBeNull();
    expect(
      screen.queryByRole("link", { name: "Tài khoản nhân sự" }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Ký blockchain" })).toBeNull();
  });

  it("shows admin work allocation links in the admin area", () => {
    navigationState.pathname = "/admin";
    render(
      <AuthUserProvider
        user={{
          id: "review-coordinator",
          email: "coordinator@cnsgroup.vn",
          roles: ["SUPER_ADMIN"],
          accountType: null,
        }}
      >
        <DashboardShell>
          <h1>Phân công thẩm định</h1>
        </DashboardShell>
      </AuthUserProvider>,
    );

    expect(
      screen.getAllByRole("link", { name: "Phân công công việc" }).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByRole("link", { name: "Phân công thẩm định" }),
    ).toBeNull();
  });

  it("keeps signed in reviewers on the public page without changing context", () => {
    navigationState.pathname = "/works";
    render(
      <AuthUserProvider
        user={{
          id: "reviewer-library",
          email: "reviewer@cnsgroup.vn",
          roles: ["MODERATOR"],
          accountType: null,
        }}
      >
        <PublicShell>
          <h1>Thư viện đề cử</h1>
        </PublicShell>
      </AuthUserProvider>,
    );

    expect(
      screen.getByRole("heading", { name: "Thư viện đề cử" }),
    ).toBeDefined();
    expect(
      screen.queryByRole("navigation", { name: "Quay lại khu vực làm việc" }),
    ).toBeNull();
    expect(
      screen
        .getByRole("navigation", { name: "Điều hướng di động" })
        .querySelector('a[href="/works"]'),
    ).not.toBeNull();
  });

  it("offers the canonical workspace from the public account menu", async () => {
    const user = userEvent.setup();
    render(
      <AuthUserProvider
        user={{
          id: "user-public",
          email: "reader@cnsgroup.vn",
          roles: [],
          accountType: "PUBLIC_USER",
        }}
      >
        <PublicShell>
          <h1>Catalog</h1>
        </PublicShell>
      </AuthUserProvider>,
    );

    await user.click(screen.getByLabelText("Mở menu tài khoản"));
    const menu = screen.getByRole("navigation", { name: "Menu tài khoản" });
    expect(
      within(menu)
        .getByRole("link", { name: "Không gian cá nhân" })
        .getAttribute("href"),
    ).toBe("/workspace");
    expect(
      within(menu).queryByRole("link", { name: "Khu vực quản trị" }),
    ).toBeNull();
  });

  it("uses the current role context instead of a generic workspace title", () => {
    navigationState.pathname = "/admin/content";
    render(
      <AuthUserProvider
        user={{
          id: "user-content-admin",
          email: "content@cnsgroup.vn",
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

  it("keeps signed-in discovery pages inside the public shell", async () => {
    navigationState.pathname = "/works";
    render(
      <PublicExperienceShell
        user={{
          id: "user-4",
          email: "reader@cnsgroup.vn",
          roles: [],
          accountType: "PUBLIC_USER",
        }}
      >
        <h1>Thư viện đề cử</h1>
      </PublicExperienceShell>,
    );

    expect(
      screen.getByRole("navigation", { name: "Điều hướng chính" }),
    ).toBeDefined();
    expect(
      within(screen.getByRole("banner")).getByText("Thành viên"),
    ).toBeDefined();
    expect(
      within(screen.getByRole("banner")).queryByText("reader@cnsgroup.vn"),
    ).toBeNull();
    const quickNavigation = screen.getByRole("navigation", {
      name: "Điều hướng di động",
    });
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Đề cử" })
        .getAttribute("aria-current"),
    ).toBe("page");
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Đề cử" })
        .getAttribute("href"),
    ).toBe("/works");
  });

  it("marks public mobile destinations and restores focus after More", async () => {
    const user = userEvent.setup();
    navigationState.pathname = "/works";
    render(
      <AuthUserProvider
        user={{
          id: "reader-library",
          email: "reader@cnsgroup.vn",
          roles: ["USER"],
          accountType: null,
        }}
      >
        <PublicShell>
          <h1>Thư viện đề cử</h1>
        </PublicShell>
      </AuthUserProvider>,
    );
    const quickNavigation = screen.getByRole("navigation", {
      name: "Điều hướng di động",
    });
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Đề cử" })
        .getAttribute("aria-current"),
    ).toBe("page");
    expect(
      within(quickNavigation)
        .getByRole("link", { name: "Cá nhân" })
        .getAttribute("href"),
    ).toBe("/workspace");
    const moreButton = within(quickNavigation).getByRole("button", {
      name: "Mở thêm mục điều hướng",
    });
    await user.click(moreButton);
    await user.keyboard("{Escape}");
    await waitFor(() => expect(document.activeElement).toBe(moreButton));
  });
});
