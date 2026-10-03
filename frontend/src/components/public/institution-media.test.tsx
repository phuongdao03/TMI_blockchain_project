import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HeritageGallery } from "./heritage-gallery";
import { WelcomeMusic } from "./welcome-music";

describe("institution media", () => {
  afterEach(() => vi.restoreAllMocks());

  it("plays the welcome music only after an explicit click", async () => {
    const play = vi
      .spyOn(HTMLMediaElement.prototype, "play")
      .mockResolvedValue();
    const pause = vi
      .spyOn(HTMLMediaElement.prototype, "pause")
      .mockImplementation(() => {});
    render(<WelcomeMusic />);

    expect(play).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Phát bản hùng ca" }),
    ).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Phát bản hùng ca" }));
    expect(play).toHaveBeenCalledOnce();
    fireEvent.click(
      screen.getByRole("button", { name: "Tạm dừng bản hùng ca" }),
    );
    expect(pause).toHaveBeenCalledOnce();
    expect(document.querySelector("audio")?.getAttribute("src")).toBe(
      "/assets/institution/welcome.mp3",
    );
  });

  it("filters the photo collection and opens a selected image", () => {
    render(<HeritageGallery />);
    expect(screen.getByRole("button", { name: /Tất cả 38/ })).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Nghi thức & sự kiện 13/ }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Kết nối & thực địa 17/ }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Văn hóa & đời sống 8/ }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", {
        name: "Lễ công bố và trao quyết định xác lập",
      }),
    ).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /Văn hóa & đời sống/ }));
    expect(
      screen.getByRole("img", { name: "Sắc màu nghề đan truyền thống" }),
    ).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Xem toàn màn hình" }));
    expect(
      screen.getByRole("dialog", { name: "Ảnh Tinh Hoa Việt" }),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: "Đóng ảnh toàn màn hình" })).toBe(
      document.activeElement,
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Xem toàn màn hình" }));
    fireEvent.click(
      screen.getByRole("button", { name: "Đóng ảnh toàn màn hình" }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
