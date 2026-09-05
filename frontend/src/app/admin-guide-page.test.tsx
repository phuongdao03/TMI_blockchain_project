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
      "Tạo yêu cầu thanh toán",
      "Ghi nhận hồ sơ trên blockchain",
      "Công bố nội dung",
      "Quản lý tài khoản nhân sự",
      "Kiểm tra lịch sử và báo cáo",
      "Xử lý tình huống thường gặp",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeDefined();
    }

    expect(screen.getByText(/chỉ công bố dấu vân tay số/i)).toBeDefined();
    expect(
      screen.getByText(/không đưa tài liệu gốc lên blockchain/i),
    ).toBeDefined();
    expect(screen.getByText(/chỉ tạo khoản phí sau khi hồ sơ/i)).toBeDefined();
    expect(
      screen.queryByText(/window\.ethereum|calldata|checksum/i),
    ).toBeNull();
    expect(container.querySelector('a[href="/council"]')).toBeNull();
  });
});
