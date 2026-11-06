import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProcessPage from "@/app/(public)/process/page";

describe("ProcessPage", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("shows the four-step preview journey without opening dossier creation", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(<ProcessPage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Hành trình đề cử Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Chuẩn bị hồ sơ/ }),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: /Gửi hồ sơ/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /Xem xét hồ sơ/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /Nhận kết quả/ })).toBeDefined();
    expect(
      screen.getByText("Cổng gửi hồ sơ được mở theo từng giai đoạn."),
    ).toBeDefined();
    expect(
      screen.getAllByRole("link", { name: "Xem thông tin mở cổng" }),
    ).toHaveLength(2);
    expect(
      screen.getAllByRole("link", { name: "Tra cứu kết quả" }),
    ).toHaveLength(2);
    expect(
      screen.queryByRole("link", { name: "Bắt đầu gửi hồ sơ" }),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /Gửi hồ sơ/ }));
    expect(screen.getAllByText(/Khi cổng gửi hồ sơ mở/)).toHaveLength(2);
    expect(
      screen.getByText(
        /Gửi đề cử không đồng nghĩa với việc chắc chắn được xác lập/i,
      ),
    ).toBeDefined();
  });

  it("shows guidance for the selected step and expands common questions", () => {
    render(<ProcessPage />);

    fireEvent.click(screen.getByRole("button", { name: /Gửi hồ sơ/ }));
    expect(screen.getByRole("region", { name: "Gửi hồ sơ" })).toBeDefined();
    expect(
      screen.getByText(/thanh toán trước khi hồ sơ chuyển sang xem xét/i),
    ).toBeDefined();

    fireEvent.click(screen.getByText("Nếu hồ sơ còn thiếu giấy tờ thì sao?"));
    expect(screen.getByText(/nếu Trung tâm yêu cầu bổ sung/i)).toBeDefined();
  });
});
