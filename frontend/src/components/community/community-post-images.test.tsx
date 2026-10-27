import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { CommunityPostImages } from "./community-post-images";

it("opens and closes an image inside an editor without nesting or submitting forms", () => {
  const submit = vi.fn((event) => event.preventDefault());
  const { container } = render(
    <form onSubmit={submit}>
      <CommunityPostImages
        postSlug="di-san"
        postTitle="Di sản"
        images={[
          {
            id: "image-1",
            url: "/api/v1/community/posts/di-san/media/image-1",
          },
        ]}
      />
    </form>,
  );
  expect(container.querySelector("form form")).toBeNull();
  const dialog = container.querySelector("dialog")!;
  dialog.showModal = vi.fn(() => dialog.setAttribute("open", ""));
  dialog.close = vi.fn(() => dialog.removeAttribute("open"));
  fireEvent.click(screen.getByRole("button", { name: "Xem lớn ảnh 1" }));
  expect(dialog.hasAttribute("open")).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Đóng ảnh" }));
  expect(dialog.hasAttribute("open")).toBe(false);
  expect(submit).not.toHaveBeenCalled();
});
