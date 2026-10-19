import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/auth/role-gate", () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => children,
}));

import AdminGuidePage from "@/app/(dashboard)/admin/guide/page";

describe("AdminGuidePage", () => {
  it("provides an internal guide for every core administration workflow", () => {
    const { container } = render(<AdminGuidePage />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Hướng dẫn quản trị" }),
    ).toBeDefined();

    for (const heading of [
      "Bắt đầu ca làm việc",
      "Quản lý hồ sơ và người dùng",
      "Tổ chức thẩm định hồ sơ",
      "Gửi thông báo thu phí",
      "Ghi nhận hồ sơ đã được duyệt",
      "Công bố nội dung",
      "Quản lý tài khoản nhân sự",
      "Quản lý nhân viên và tính lương",
      "Kiểm tra lịch sử và báo cáo",
      "Xử lý tình huống thường gặp",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeDefined();
    }

    expect(screen.getByText(/Bản ghi giúp đối chiếu mã hồ sơ/i)).toBeDefined();
    expect(container.textContent).not.toMatch(
      /blockchain|PayOS|MetaMask|Polygon|Firebase|wallet|webhook/i,
    );
    expect(screen.getByText(/chỉ tạo khoản phí sau khi hồ sơ/i)).toBeDefined();
    expect(screen.getByText(/quản trị viên Tinh Hoa Việt/i)).toBeDefined();
    expect(screen.queryByText(/CNS/i)).toBeNull();
    expect(
      screen
        .getByRole("link", { name: "Xem hướng dẫn theo chủ đề" })
        .getAttribute("href"),
    ).toBe("/help");
    expect(
      screen
        .getByRole("link", { name: "Mở hàng đợi thẩm định" })
        .getAttribute("href"),
    ).toBe("/admin/reviews");
    expect(
      screen.queryByText(/window\.ethereum|calldata|checksum/i),
    ).toBeNull();
    expect(container.querySelector('a[href="/council"]')).toBeNull();
  });
});
