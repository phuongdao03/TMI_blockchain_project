import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CertificateOrbit } from "@/components/visual/certificate-orbit";

describe("CertificateOrbit", () => {
  it("presents the TMI evidence register as one accessible visual", () => {
    render(<CertificateOrbit />);

    expect(
      screen.getByRole("img", {
        name: "Hồ sơ đề cử minh họa",
      }),
    ).toBeDefined();
    expect(screen.getByText("DẤU VÂN TAY DỮ LIỆU")).toBeDefined();
    expect(screen.getByText("Sẵn sàng xác minh")).toBeDefined();
  });

  it("uses specific editorial copy in preview mode", () => {
    render(<CertificateOrbit preview />);

    expect(screen.getByText("DẤU ẤN TINH HOA VIỆT")).toBeDefined();
    expect(screen.getByText("Giá trị được hình thành")).toBeDefined();
    expect(screen.getByText("GIÁ TRỊ ĐƯỢC GÌN GIỮ VÀ LAN TỎA")).toBeDefined();
    expect(screen.getByText("Tinh hoa Việt")).toBeDefined();
    expect(screen.queryByText(/sơn mài/i)).toBeNull();
    expect(screen.queryByText("NỘI DUNG GIỚI THIỆU")).toBeNull();
    expect(screen.queryByText("Chưa phát hành")).toBeNull();
  });
});
