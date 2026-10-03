import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProposalViewer } from "./proposal-viewer";

describe("ProposalViewer", () => {
  it("navigates all 53 local pages with controls, page input, and table of contents", () => {
    render(<ProposalViewer />);

    expect(screen.getByRole("status").textContent).toContain("Trang 1 / 53");
    expect(
      screen
        .getByRole("button", { name: "Trang trước" })
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Trang sau" }));
    expect(screen.getByRole("status").textContent).toContain("Trang 2 / 53");
    expect(
      screen.getByRole("img", { name: /trang 2 trên 53/i }).getAttribute("src"),
    ).toContain("page-02.webp");

    fireEvent.click(screen.getByRole("button", { name: "Mục lục" }));
    const outline = screen.getByRole("navigation", {
      name: "Mục lục proposal",
    });
    fireEvent.click(
      within(outline).getByRole("button", { name: /Lời mời đồng hành/ }),
    );
    expect(screen.getByRole("status").textContent).toContain("Trang 52 / 53");

    fireEvent.change(
      screen.getByRole("spinbutton", { name: "Số trang muốn xem" }),
      { target: { value: "53" } },
    );
    fireEvent.submit(
      screen
        .getByRole("spinbutton", { name: "Số trang muốn xem" })
        .closest("form")!,
    );
    expect(screen.getByRole("status").textContent).toContain("Trang 53 / 53");
    expect(
      screen
        .getByRole("button", { name: "Trang sau" })
        .hasAttribute("disabled"),
    ).toBe(true);
  });

  it("supports keyboard navigation and bounded zoom", () => {
    render(<ProposalViewer />);
    const reader = screen.getByRole("region", { name: "Trình xem proposal" });
    fireEvent.keyDown(reader, { key: "ArrowRight" });
    expect(screen.getByRole("status").textContent).toContain("Trang 2 / 53");
    fireEvent.click(screen.getByRole("button", { name: "Phóng to trang" }));
    expect(
      screen.getByRole("button", { name: "Đặt lại mức phóng to" }).textContent,
    ).toBe("125%");
    fireEvent.click(
      screen.getByRole("button", { name: "Đặt lại mức phóng to" }),
    );
    expect(
      screen.getByRole("button", { name: "Đặt lại mức phóng to" }).textContent,
    ).toBe("100%");
  });

  it("keeps fullscreen reading available when the browser lacks the Fullscreen API", () => {
    render(<ProposalViewer />);
    const reader = screen.getByRole("region", { name: "Trình xem proposal" });
    fireEvent.click(screen.getByRole("button", { name: "Đọc toàn màn hình" }));
    expect(reader.classList.contains("proposal-reader--expanded")).toBe(true);
    fireEvent.keyDown(reader, { key: "Escape" });
    expect(reader.classList.contains("proposal-reader--expanded")).toBe(false);
  });
});
