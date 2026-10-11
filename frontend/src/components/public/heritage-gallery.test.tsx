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
  ).toHaveLength(38);
});

it("shows loading feedback while a gallery image changes", async () => {
  render(<HeritageGallery />);

  expect(await screen.findByText("Đang tải hình ảnh…")).toBeDefined();
  fireEvent.load(screen.getByAltText("Lễ công bố và trao quyết định xác lập"));
  await waitFor(() =>
    expect(screen.queryByText("Đang tải hình ảnh…")).toBeNull(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Ảnh tiếp theo" }));
  expect(screen.getByText("Đang tải hình ảnh…")).toBeDefined();
});
