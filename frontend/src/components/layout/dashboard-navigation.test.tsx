import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthUserProvider } from "@/lib/auth/user-context";

import { DashboardNavigation } from "./dashboard-navigation";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("DashboardNavigation work-allocation migration", () => {
  it("shows community moderation only to users with its explicit capability", () => {
    render(
      <AuthUserProvider
        user={{
          id: "community-moderator",
          email: "moderator@example.com",
          roles: ["MODERATOR"],
          permissions: ["community.moderate"],
          isEmployee: false,
          accountType: null,
        }}
      >
        <DashboardNavigation
          area="admin"
          roles={["MODERATOR"]}
          showQuickNavigation={false}
        />
      </AuthUserProvider>,
    );

    expect(
      screen
        .getByRole("link", { name: "Kiểm duyệt cộng đồng" })
        .getAttribute("href"),
    ).toBe("/admin/community");
  });

  it("does not show community moderation to a moderator without the capability", () => {
    render(
      <AuthUserProvider
        user={{
          id: "regular-moderator",
          email: "moderator@example.com",
          roles: ["MODERATOR"],
          permissions: [],
          isEmployee: false,
          accountType: null,
        }}
      >
        <DashboardNavigation
          area="admin"
          roles={["MODERATOR"]}
          showQuickNavigation={false}
        />
      </AuthUserProvider>,
    );

    expect(
      screen.queryByRole("link", { name: "Kiểm duyệt cộng đồng" }),
    ).toBeNull();
  });

  it("shows community administration to users with the management capability", () => {
    const { container } = render(
      <AuthUserProvider
        user={{
          id: "community-manager",
          email: "manager@example.com",
          roles: [],
          permissions: ["community.manage"],
          isEmployee: false,
          accountType: null,
        }}
      >
        <DashboardNavigation area="admin" showQuickNavigation={false} />
      </AuthUserProvider>,
    );

    expect(
      container.querySelector('a[href="/admin/community"]'),
    ).not.toBeNull();
  });

  it("keeps community in the mobile quick navigation for signed-in members", () => {
    render(
      <AuthUserProvider
        user={{
          id: "member-with-community",
          email: "member@example.com",
          roles: ["USER"],
          permissions: [],
          isEmployee: false,
          accountType: "PUBLIC_USER",
        }}
      >
        <DashboardNavigation roles={["USER"]} showPrimaryNavigation={false} />
      </AuthUserProvider>,
    );

    expect(
      screen
        .getByRole("navigation", { name: "Điều hướng nhanh" })
        .querySelector('a[href="/community"]'),
    ).not.toBeNull();
  });

  it("gives Super Admin one unified work-allocation destination", () => {
    render(
      <DashboardNavigation
        area="admin"
        roles={["SUPER_ADMIN"]}
        showQuickNavigation={false}
      />,
    );

    expect(
      screen
        .getByRole("link", { name: "Phân công công việc" })
        .getAttribute("href"),
    ).toBe("/admin/work-allocations");
    expect(
      screen.queryByRole("link", { name: "Phân công thẩm định" }),
    ).toBeNull();
    expect(screen.queryByRole("link", { name: "Công việc" })).toBeNull();
    expect(
      screen.getByRole("link", { name: "Bảng lương" }).getAttribute("href"),
    ).toBe("/admin/payroll");
  });

  it("gives Moderator the personal allocation workspace", () => {
    render(
      <AuthUserProvider
        user={{
          id: "regular-moderator",
          email: "moderator@example.com",
          roles: ["MODERATOR"],
          isEmployee: false,
          accountType: null,
        }}
      >
        <DashboardNavigation
          roles={["MODERATOR"]}
          showQuickNavigation={false}
        />
      </AuthUserProvider>,
    );

    expect(
      screen
        .getByRole("link", { name: "Công việc được giao" })
        .getAttribute("href"),
    ).toBe("/work-allocations");
    expect(screen.queryByRole("link", { name: "Hồ sơ đánh giá" })).toBeNull();
    expect(
      screen.getByRole("link", { name: "Việc thẩm định" }).getAttribute("href"),
    ).toBe("/reviews");
    expect(
      screen.getByRole("link", { name: "Chấm công" }).getAttribute("href"),
    ).toBe("/attendance");
    expect(screen.queryByRole("link", { name: "Nghỉ phép" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Tăng ca" })).toBeNull();
  });

  it("shows Moderator HR self-service only with a linked employee profile", () => {
    render(
      <AuthUserProvider
        user={{
          id: "employee-moderator",
          email: "moderator@example.com",
          roles: ["MODERATOR"],
          isEmployee: true,
          accountType: null,
        }}
      >
        <DashboardNavigation
          roles={["MODERATOR"]}
          showQuickNavigation={false}
        />
      </AuthUserProvider>,
    );

    expect(
      screen.getByRole("link", { name: "Chấm công" }).getAttribute("href"),
    ).toBe("/attendance");
    expect(
      screen.getByRole("link", { name: "Nghỉ phép" }).getAttribute("href"),
    ).toBe("/leave");
    expect(
      screen.getByRole("link", { name: "Tăng ca" }).getAttribute("href"),
    ).toBe("/overtime");
  });

  it("exposes the admin dossier intake queue beside other work", () => {
    render(
      <DashboardNavigation
        area="admin"
        roles={["SUPER_ADMIN"]}
        showQuickNavigation={false}
      />,
    );

    expect(
      screen
        .getByRole("link", { name: "Tiếp nhận hồ sơ" })
        .getAttribute("href"),
    ).toBe("/admin/reviews");
  });

  it("shows HR self-service links to USER employees without reviewer actions", () => {
    render(
      <AuthUserProvider
        user={{
          id: "employee-user",
          email: "employee@example.com",
          roles: ["USER"],
          isEmployee: true,
          accountType: null,
        }}
      >
        <DashboardNavigation roles={["USER"]} showQuickNavigation={false} />
      </AuthUserProvider>,
    );

    expect(
      screen.getByRole("link", { name: "Chấm công" }).getAttribute("href"),
    ).toBe("/attendance");
    expect(
      screen.getByRole("link", { name: "Nghỉ phép" }).getAttribute("href"),
    ).toBe("/leave");
    expect(
      screen.getByRole("link", { name: "Tăng ca" }).getAttribute("href"),
    ).toBe("/overtime");
    expect(
      screen.queryByRole("link", { name: "Công việc được giao" }),
    ).toBeNull();
  });

  it("hides HR self-service links until USER is configured as an employee", () => {
    render(
      <AuthUserProvider
        user={{
          id: "regular-user",
          email: "user@example.com",
          roles: ["USER"],
          isEmployee: false,
          accountType: null,
        }}
      >
        <DashboardNavigation roles={["USER"]} showQuickNavigation={false} />
      </AuthUserProvider>,
    );

    expect(screen.queryByRole("link", { name: "Chấm công" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Nghỉ phép" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Tăng ca" })).toBeNull();
  });

  it("shows the applicant preview without employee functions", () => {
    render(
      <DashboardNavigation
        previewRole="USER"
        roles={["USER"]}
        showQuickNavigation={false}
      />,
    );

    expect(screen.getByRole("link", { name: "Hồ sơ của tôi" })).toBeDefined();
    expect(screen.queryByRole("link", { name: "Chấm công" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Nghỉ phép" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Tăng ca" })).toBeNull();
  });

  it("does not expose allocation administration from a misassigned permission", () => {
    render(
      <AuthUserProvider
        user={{
          id: "moderator-with-misassigned-permission",
          email: "moderator@example.com",
          roles: ["MODERATOR"],
          permissions: ["work.allocations.manage"],
          accountType: null,
        }}
      >
        <DashboardNavigation
          roles={["MODERATOR"]}
          showQuickNavigation={false}
        />
      </AuthUserProvider>,
    );

    expect(
      screen.queryByRole("link", { name: "Phân công công việc" }),
    ).toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Công việc được giao" })
        .getAttribute("href"),
    ).toBe("/work-allocations");
  });
});
