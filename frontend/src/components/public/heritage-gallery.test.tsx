import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it } from "vitest";

import { HeritageGallery } from "@/components/public/heritage-gallery";

it("shows loading feedback while a gallery image changes", async () => {
  render(<HeritageGallery />);

  expect(screen.getByText("Đang tải hình ảnh…")).toBeDefined();
  fireEvent.load(screen.getByAltText("Lễ công bố và trao quyết định xác lập"));
  await waitFor(() =>
    expect(screen.queryByText("Đang tải hình ảnh…")).toBeNull(),
  );

  fireEvent.click(screen.getByRole("button", { name: "Ảnh tiếp theo" }));
  expect(screen.getByText("Đang tải hình ảnh…")).toBeDefined();
});
