import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { ImageCoverPicker } from "./image-cover-picker";

vi.mock("@/lib/api/client", () => ({
  publicWorkAdminApi: {
    configureCover: vi.fn().mockResolvedValue({}),
    attachMedia: vi.fn(),
  },
}));

it("shows explicit image sources and a named default cover when no public images exist", () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ImageCoverPicker
        workId="work"
        title="Bản thu âm"
        category="Âm nhạc"
        images={[]}
        items={[]}
        onThumbnail={vi.fn()}
        onChanged={vi.fn()}
      />
    </QueryClientProvider>,
  );
  expect(screen.getByRole("button", { name: "Chọn ảnh đã nộp" })).toBeDefined();
  expect(
    screen.getByRole("button", { name: "Tải ảnh bìa riêng" }),
  ).toBeDefined();
  expect(screen.getByLabelText("Bìa mặc định: Bản thu âm")).toBeDefined();
});

it("opens an image-only uploader without publishing the work", async () => {
  const user = userEvent.setup();
  const select = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ImageCoverPicker
        workId="work"
        title="Bản thu âm"
        category="Âm nhạc"
        images={[]}
        items={[]}
        onThumbnail={select}
        onChanged={vi.fn()}
      />
    </QueryClientProvider>,
  );
  await user.click(screen.getByRole("button", { name: "Tải ảnh bìa riêng" }));
  const input = screen.getByLabelText("Chọn ảnh bìa riêng");
  expect(input.getAttribute("accept")).toBe("image/jpeg,image/png,image/webp");
  expect(select).not.toHaveBeenCalled();
});
