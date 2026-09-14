import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import UserGuidePage from "@/app/(public)/guide/page";

describe("UserGuidePage", () => {
  it("documents the current public and applicant journeys in plain language", () => {
    render(<UserGuidePage />);
    expect(screen.getByRole("heading", { level: 1, name: "Hướng dẫn sử dụng Đề cử Tinh Hoa Việt" })).toBeDefined();
    for (const heading of [
      "Về Tổ chức Đề cử và Xác lập Tinh Hoa Việt",
      "Khám phá đề cử",
      "Tạo tài khoản và đăng nhập",
      "Tạo và gửi hồ sơ đề cử",
      "Theo dõi hồ sơ, bổ sung và lệ phí",
      "Tra cứu chứng thư, QR và lưu trữ blockchain",
      "Cài ứng dụng trên thiết bị",
      "Bảo vệ tài khoản và nhận hỗ trợ",
    ]) expect(screen.getByRole("heading", { name: heading })).toBeDefined();

    expect(screen.getByText(/không lưu.*tệp gốc.*tài liệu cá nhân/i)).toBeDefined();
    expect(screen.getByText(/tìm kiếm, ghi nhận và lan tỏa những giá trị tiêu biểu/i)).toBeDefined();
    expect(screen.getByRole("heading", { name: "Chứng thư mang lại điều gì?" })).toBeDefined();
    expect(screen.getByRole("heading", { name: "Thông tin nào được công khai?" })).toBeDefined();
    expect(screen.getByText(/không thanh toán lần hai/i)).toBeDefined();
    expect(screen.queryByText(/PayOS|Chrome|Edge|Safari|Google Play|App Store/i)).toBeNull();
    expect(screen.queryByText(/VERIFIER_ROLE|window\.ethereum|checksum|webhook/i)).toBeNull();
    expect(screen.getByRole("link", { name: "Mở thư viện đề cử" }).getAttribute("href")).toBe("/works");
    expect(screen.getByRole("link", { name: "Tra cứu chứng thư" }).getAttribute("href")).toBe("/verify");
    expect(screen.getByRole("link", { name: "Xem hướng dẫn cài đặt" }).getAttribute("href")).toBe("/install");
  });
});
