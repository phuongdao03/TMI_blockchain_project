import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AccountGuidePage from "@/app/(dashboard)/help/page";
import { AuthUserProvider } from "@/lib/auth/user-context";

function renderFor(roles: string[], isEmployee = false) {
  render(
    <AuthUserProvider
      user={{
        id: "account-1",
        email: "test@example.vn",
        roles,
        isEmployee,
        accountType: null,
      }}
    >
      <AccountGuidePage />
    </AuthUserProvider>,
  );
}

describe("account guides", () => {
  it("explains role acceptance, review assignments and employee linkage to a moderator", () => {
    renderFor(["MODERATOR"]);
    expect(
      screen.getByRole("heading", {
        name: "Hướng dẫn dành cho nhân viên kiểm duyệt",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "Nhận quyền kiểm duyệt" }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "Xử lý hồ sơ được phân công" }),
    ).toBeDefined();
    expect(
      screen.getByText(/quyền kiểm duyệt không tự tạo hồ sơ lao động/),
    ).toBeDefined();
  });

  it("shows account tasks for applicants without changing the public guide", () => {
    renderFor(["USER"]);
    expect(
      screen.getByRole("heading", { name: "Hướng dẫn tài khoản gửi hồ sơ" }),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Mở hồ sơ của tôi" })
        .getAttribute("href"),
    ).toBe("/dossiers");
    expect(
      screen
        .getByRole("link", { name: "trang hướng dẫn công khai" })
        .getAttribute("href"),
    ).toBe("/guide");
  });

  it("shows search and verification tasks to a lookup account", () => {
    renderFor(["PUBLIC_USER"]);
    expect(
      screen.getByRole("heading", { name: "Hướng dẫn tài khoản tra cứu" }),
    ).toBeDefined();
    expect(
      screen
        .getAllByRole("link", { name: "Tra cứu chứng thư" })
        .some((link) => link.getAttribute("href") === "/verify"),
    ).toBe(true);
  });
});
