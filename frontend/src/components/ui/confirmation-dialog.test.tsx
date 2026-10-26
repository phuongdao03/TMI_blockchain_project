import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";

describe("ConfirmationDialog", () => {
  it("renders outside the page and restores scrolling after closing", () => {
    const { container, unmount } = render(
      <ConfirmationDialog
        confirmLabel="Xác nhận"
        description="Kiểm tra thanh toán."
        isPending={false}
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
        open
        title="Thanh toán"
      />,
    );
    expect(container.contains(screen.getByRole("dialog"))).toBe(false);
    expect(document.body.style.overflow).toBe("hidden");
    unmount();
    expect(document.body.style.overflow).toBe("");
  });
  it("moves focus to the primary action and closes with Escape", async () => {
    const user = userEvent.setup();
    const cancel = vi.fn();

    render(
      <ConfirmationDialog
        confirmLabel="Xác nhận"
        description="Kiểm tra nội dung trước khi tiếp tục."
        isPending={false}
        onCancel={cancel}
        onConfirm={vi.fn()}
        open
        title="Xác nhận thao tác"
      />,
    );

    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Xác nhận" }),
    );
    await user.keyboard("{Escape}");
    expect(cancel).toHaveBeenCalledTimes(1);
  });

  it("announces the pending action and disables both controls", () => {
    render(
      <ConfirmationDialog
        confirmLabel="Xác nhận"
        description="Kiểm tra nội dung trước khi tiếp tục."
        isPending
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
        open
        title="Xác nhận thao tác"
      />,
    );

    expect(
      (screen.getByRole("button", { name: "Đang gửi…" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
    expect(
      (screen.getByRole("button", { name: "Quay lại" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
});
