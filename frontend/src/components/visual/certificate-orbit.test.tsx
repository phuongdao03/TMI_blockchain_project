import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CertificateOrbit } from "@/components/visual/certificate-orbit";

describe("CertificateOrbit", () => {
  it("describes the information that may be publicly displayed without fabricating a certificate", () => {
    render(<CertificateOrbit />);

    expect(
      screen.getByRole("img", {
        name: "Sơ đồ phạm vi thông tin công bố trên nền tảng Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(screen.getByText("PHẠM VI HIỂN THỊ")).toBeDefined();
    expect(screen.getByText("THÔNG TIN CÔNG BỐ")).toBeDefined();
    expect(screen.getByText("Thông tin đã được phê duyệt")).toBeDefined();
    expect(screen.getByText("Đề cử & giới thiệu")).toBeDefined();
    expect(screen.getByText("Mã tra cứu")).toBeDefined();
    expect(screen.getByText("Quyết định xử lý")).toBeDefined();
    expect(screen.queryByText("THÔNG TIN MINH HỌA")).toBeNull();
    expect(screen.queryByText("THV–VN–2026–0812")).toBeNull();
    expect(screen.queryByText("Sẵn sàng xác minh")).toBeNull();
  });
});
