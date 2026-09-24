import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthUserProvider } from "@/lib/auth/user-context";

import { DashboardNavigation } from "./dashboard-navigation";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

describe("DashboardNavigation work-allocation migration", () => {
  it("gives Super Admin one unified work-allocation destination", () => {
    render(
      <DashboardNavigation
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
      <DashboardNavigation roles={["MODERATOR"]} showQuickNavigation={false} />,
    );

    expect(
      screen
        .getByRole("link", { name: "Công việc được giao" })
        .getAttribute("href"),
    ).toBe("/work-allocations");
    expect(screen.queryByRole("link", { name: "Hồ sơ đánh giá" })).toBeNull();
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
