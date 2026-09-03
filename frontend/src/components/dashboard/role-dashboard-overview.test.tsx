import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RoleDashboardOverview } from "@/components/dashboard/role-dashboard-overview";

describe("RoleDashboardOverview", () => {
  it("renders browse-only discovery actions for a public user", () => {
    render(
      <RoleDashboardOverview accountType="PUBLIC_USER" persona="VIEWER" />,
    );

    expect(screen.getByRole("link", { name: /Tìm kiếm đề cử/i })).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Gửi tác phẩm hoặc hồ sơ/i }),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: /Tạo hồ sơ mới/i })).toBeNull();
    expect(screen.queryByText(/đăng ký đúng loại tài khoản/i)).toBeNull();
  });

  it.each([
    ["MODERATOR", "Hàng đợi thẩm định", "Mở hàng đợi thẩm định"],
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

  it("keeps blockchain signing out of the moderator workspace", () => {
    render(<RoleDashboardOverview persona="MODERATOR" />);

    expect(screen.queryByRole("link", { name: /Ký blockchain/i })).toBeNull();
  });

  it("keeps the landing page focused on a single primary action", () => {
    render(<RoleDashboardOverview persona="SUPER_ADMIN" />);

    expect(screen.queryByText("Việc cần làm tiếp theo")).toBeNull();
    expect(screen.queryByText("Sau hành động chính")).toBeNull();
    expect(screen.queryByRole("link", { name: /Ký blockchain/i })).toBeNull();
  });
});
