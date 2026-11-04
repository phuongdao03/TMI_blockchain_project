import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { HeritageGallery } from "@/components/public/heritage-gallery";

afterEach(() => vi.unstubAllGlobals());

it("does not spin for a lazy image before the gallery nears the viewport", async () => {
  let reveal: IntersectionObserverCallback | undefined;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        reveal = callback;
      }
      observe() {}
      disconnect() {}
    },
  );

  render(<HeritageGallery />);
  expect(
    (
      screen.getByAltText(
        "Lễ công bố và trao quyết định xác lập",
      ) as HTMLImageElement
    ).style.opacity,
  ).toBe("");
  expect(
    screen.getByRole("group", { name: "Chọn ảnh trong bộ sưu tập" }),
  ).toBeDefined();
  expect(screen.queryByText("Đang tải hình ảnh…")).toBeNull();
  expect(
    document.querySelectorAll(".heritage-gallery__thumbnails button"),
  ).toHaveLength(0);
  if (!reveal) throw new Error("Gallery observer was not attached");
  reveal(
    [{ isIntersecting: true } as IntersectionObserverEntry],
    {} as IntersectionObserver,
  );
  await waitFor(() =>
    expect(screen.getByText("Đang tải hình ảnh…")).toBeDefined(),
  );
  expect(
    document.querySelectorAll(".heritage-gallery__thumbnails button"),
  ).toHaveLength(6);
});

it("shows loading feedback while a gallery image changes", async () => {
  render(<HeritageGallery />);

  expect(await screen.findByText("Đang tải hình ảnh…")).toBeDefined();
  const firstImage = screen.getByAltText(
    "Lễ công bố và trao quyết định xác lập",
  );
  const trigger = screen.getByRole("button", {
    name: "Xem ảnh: Lễ công bố và trao quyết định xác lập",
  });
  expect(trigger.getAttribute("data-image-loaded")).toBe("false");
  fireEvent.load(firstImage);
  await waitFor(() =>
    expect(screen.queryByText("Đang tải hình ảnh…")).toBeNull(),
  );
  expect(trigger.getAttribute("data-image-loaded")).toBe("true");

  fireEvent.click(screen.getByRole("button", { name: "Ảnh tiếp theo" }));
  expect(screen.getByText("Đang tải hình ảnh…")).toBeDefined();
});

it("advances the inline gallery on a horizontal swipe", () => {
  render(<HeritageGallery />);
  const image = screen.getByRole("button", {
    name: "Xem ảnh: Lễ công bố và trao quyết định xác lập",
  });

  fireEvent.touchStart(image, {
    touches: [{ clientX: 180, clientY: 100 }],
  });
  fireEvent.touchEnd(image, {
    changedTouches: [{ clientX: 100, clientY: 108 }],
  });

  expect(
    screen.getByRole("button", {
      name: "Xem ảnh: Trao quyết định trên sân khấu",
    }),
  ).toBeDefined();
  expect(screen.getByText("02 / 38")).toBeDefined();
});

it("does not advance the inline gallery on a vertical gesture", () => {
  render(<HeritageGallery />);
  const image = screen.getByRole("button", {
    name: "Xem ảnh: Lễ công bố và trao quyết định xác lập",
  });

  fireEvent.touchStart(image, {
    touches: [{ clientX: 150, clientY: 100 }],
  });
  fireEvent.touchEnd(image, {
    changedTouches: [{ clientX: 158, clientY: 20 }],
  });

  expect(
    screen.getByRole("button", {
      name: "Xem ảnh: Lễ công bố và trao quyết định xác lập",
    }),
  ).toBeDefined();
  expect(screen.getByText("01 / 38")).toBeDefined();
});

it("keeps keyboard navigation, zoom, body scroll and focus coherent in the lightbox", async () => {
  render(<HeritageGallery />);
  const trigger = screen.getByRole("button", { name: "Xem toàn màn hình" });
  trigger.focus();
  fireEvent.click(trigger);
  expect(document.body.style.overflow).toBe("hidden");
  expect(screen.getByText("Ảnh 1/38")).toBeDefined();
  fireEvent.keyDown(document, { key: "ArrowRight" });
  expect(screen.getByText("Ảnh 2/38")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Phóng to ảnh" }));
  expect(
    screen
      .getByRole("button", { name: "Phóng to ảnh" })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(document.activeElement).toBe(trigger);
  expect(document.body.style.overflow).not.toBe("hidden");
});

it("offers a retry after the selected image fails", () => {
  render(<HeritageGallery />);
  fireEvent.error(screen.getByAltText("Lễ công bố và trao quyết định xác lập"));
  expect(screen.getByRole("alert").textContent).toContain("Chưa thể tải ảnh");
  fireEvent.click(screen.getByRole("button", { name: "Thử tải lại ảnh" }));
  expect(screen.queryByRole("alert")).toBeNull();
});
