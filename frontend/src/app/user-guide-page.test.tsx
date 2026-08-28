import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import UserGuidePage from "@/app/(public)/guide/page";

describe("UserGuidePage", () => {
  it("helps visitors choose the correct journey and complete core tasks", () => {
    render(<UserGuidePage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Hướng dẫn sử dụng Đề cử Tinh Hoa Việt",
      }),
    ).toBeDefined();

    const journeys = screen.getByLabelText("Chọn hướng dẫn phù hợp");
    expect(within(journeys).getByText(/dành cho người xem/i)).toBeDefined();
    expect(
      within(journeys).getByText(/dành cho người gửi hồ sơ/i),
    ).toBeDefined();
    expect(within(journeys).queryByText(/dành cho nhân sự/i)).toBeNull();

    for (const heading of [
      "Khám phá tác phẩm",
      "Tạo tài khoản và đăng nhập",
      "Tạo và gửi hồ sơ",
      "Theo dõi hồ sơ và thông báo",
      "Tra cứu chứng thư và mã QR",
      "Bảo vệ tài khoản và dữ liệu",
      "Khi bạn cần hỗ trợ",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeDefined();
    }

    expect(screen.getByText(/không lưu tệp gốc.*blockchain/i)).toBeDefined();
    expect(screen.getByText(/không bao giờ yêu cầu.*khóa ví/i)).toBeDefined();
    expect(screen.queryByText(/không nhận được email xác minh/i)).toBeNull();
    expect(
      screen.getByText(
        /thông báo nghiệp vụ chỉ hiển thị trong tài khoản trên website/i,
      ),
    ).toBeDefined();
    expect(
      screen.getByText(/quên mật khẩu hoặc chưa nhận được email đặt lại/i),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Mở thư viện đề cử" })
        .getAttribute("href"),
    ).toBe("/works");
    expect(
      screen
        .getAllByRole("link", { name: "Tra cứu chứng thư" })
        .some((link) => link.getAttribute("href") === "/verify"),
    ).toBe(true);
  });
});
