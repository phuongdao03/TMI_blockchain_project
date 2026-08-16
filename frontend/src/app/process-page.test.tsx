import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ProcessPage from "@/app/(public)/process/page";

describe("ProcessPage", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("describes the public V1 journey without presenting submission as active", () => {
    vi.stubEnv("NEXT_PUBLIC_RELEASE_MODE", "preview");
    render(<ProcessPage />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Hành trình từ một đề cử đến giá trị được lan tỏa.",
      }),
    ).toBeDefined();
    expect(screen.getByText("Khám phá đề cử")).toBeDefined();
    expect(screen.getByText("Tìm hiểu câu chuyện")).toBeDefined();
    expect(screen.getByText("Theo dõi chương trình")).toBeDefined();
    expect(screen.getByText("Cổng gửi đề cử sắp ra mắt")).toBeDefined();
    expect(
      screen.getByText(/người tham gia sẽ có thể chuẩn bị/i),
    ).toBeDefined();
    expect(screen.queryByText(/cá nhân và đơn vị/i)).toBeNull();
    expect(screen.queryByText("Mở hồ sơ gửi tác phẩm")).toBeNull();
  });
});
