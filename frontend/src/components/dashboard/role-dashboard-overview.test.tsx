import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RoleDashboardOverview } from "@/components/dashboard/role-dashboard-overview";

describe("RoleDashboardOverview", () => {
  it("renders browse-only discovery actions for a public user", () => {
    render(
      <RoleDashboardOverview accountType="PUBLIC_USER" persona="PUBLIC" />,
    );

    expect(screen.getByRole("link", { name: /Tìm kiếm đề cử/i })).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Gửi tác phẩm hoặc hồ sơ/i }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: /Tạo hồ sơ mới/i })).toBeNull();
    expect(screen.queryByText(/đăng ký đúng loại tài khoản/i)).toBeNull();
  });

  it.each([
    ["REVIEWER", "Hàng đợi thẩm định", "Mở hàng đợi thẩm định"],
    ["COUNCIL", "Phiên xét duyệt Hội đồng", "Mở phiên Hội đồng"],
    ["ADMIN", "Điều hành nền tảng", "Mở bảng vận hành"],
    ["SUPER_ADMIN", "Điều hành toàn hệ thống", "Mở bảng điều hành"],
  ] as const)(
    "renders the permitted landing actions for %s",
    (persona, title, action) => {
      render(<RoleDashboardOverview persona={persona} />);

      expect(
        screen.getByRole("heading", { level: 1, name: title }),
      ).toBeDefined();
      expect(
        screen.getByRole("link", { name: new RegExp(action) }),
      ).toBeDefined();
    },
  );

  it("does not expose operations controls to a content-only admin", () => {
    render(<RoleDashboardOverview persona="ADMIN" roles={["CONTENT_ADMIN"]} />);

    expect(
      screen.getByRole("link", { name: /Mở quản trị nội dung/i }),
    ).toBeDefined();
    expect(
      screen.queryByRole("link", { name: /Mở bảng vận hành/i }),
    ).toBeNull();
  });
});
