import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminAnnouncementWorkspace } from "@/components/admin/admin-announcement-workspace";

const preview = vi.fn();
const send = vi.fn();
const list = vi.fn();
vi.mock("@/lib/api/client", () => ({
  adminAnnouncementsApi: {
    preview: (...args: unknown[]) => preview(...args),
    send: (...args: unknown[]) => send(...args),
  },
  adminUsersApi: { list: (...args: unknown[]) => list(...args) },
  ApiError: class ApiError extends Error {},
}));

describe("AdminAnnouncementWorkspace", () => {
  beforeEach(() => {
    preview.mockReset();
    send.mockReset();
    list.mockReset();
  });

  it("previews the audience and requires confirmation before sending", async () => {
    preview.mockResolvedValue({ recipientCount: 2 });
    send.mockResolvedValue({ recipientCount: 2, campaignId: "campaign" });
    const user = userEvent.setup();
    render(<AdminAnnouncementWorkspace />);

    await user.type(screen.getByLabelText("Tiêu đề"), "Lịch làm việc mới");
    await user.type(
      screen.getByLabelText("Nội dung"),
      "Vui lòng kiểm tra lịch tuần tới.",
    );
    await user.click(screen.getByRole("button", { name: "Xem số người nhận" }));
    expect(preview).toHaveBeenCalledWith({
      audience: "ALL",
      recipientUserId: undefined,
    });
    expect(
      await screen.findByText("2 tài khoản sẽ nhận thông báo."),
    ).toBeDefined();
    expect(
      screen
        .getByRole("button", { name: "Gửi thông báo" })
        .hasAttribute("disabled"),
    ).toBe(true);
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Gửi thông báo" }));
    expect(send).toHaveBeenCalledWith(
      expect.objectContaining({ audience: "ALL", title: "Lịch làm việc mới" }),
    );
    expect(await screen.findByText("Đã gửi cho 2 tài khoản.")).toBeDefined();
  });

  it("requires a fresh recipient selection when the account search changes", async () => {
    const recipient = {
      id: "8bcc214f-dc43-47cc-8d73-0f2d867e98f6",
      email: "first@example.com",
      fullName: "First recipient",
    };
    list.mockResolvedValue({ data: [recipient] });
    preview.mockResolvedValue({ recipientCount: 1 });
    const user = userEvent.setup();
    render(<AdminAnnouncementWorkspace />);

    await user.click(screen.getByRole("button", { name: /Một người/ }));
    await user.type(screen.getByLabelText("Tìm tài khoản"), "first");
    await user.click(screen.getByRole("button", { name: /^Tìm$/ }));
    await user.click(
      await screen.findByRole("button", { name: /First recipient/ }),
    );
    await user.type(screen.getByLabelText("Tiêu đề"), "Lịch mới");
    await user.type(screen.getByLabelText("Nội dung"), "Nội dung thông báo");
    await user.click(screen.getByRole("button", { name: "Xem số người nhận" }));
    await screen.findByRole("checkbox");

    await user.type(screen.getByLabelText("Tìm tài khoản"), "second");
    expect(screen.queryByText(/Đã chọn: First recipient/)).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(
      screen
        .getByRole("button", { name: "Xem số người nhận" })
        .hasAttribute("disabled"),
    ).toBe(true);
    expect(send).not.toHaveBeenCalled();
  });

  it("keeps the draft fixed while the recipient preview is in progress", async () => {
    let finishPreview: (result: { recipientCount: number }) => void = () => {};
    preview.mockImplementation(
      () =>
        new Promise<{ recipientCount: number }>((resolve) => {
          finishPreview = resolve;
        }),
    );
    const user = userEvent.setup();
    render(<AdminAnnouncementWorkspace />);
    await user.type(screen.getByLabelText("Tiêu đề"), "Lịch mới");
    await user.type(screen.getByLabelText("Nội dung"), "Nội dung thông báo");
    await user.click(screen.getByRole("button", { name: "Xem số người nhận" }));

    expect(screen.getByLabelText("Tiêu đề").hasAttribute("disabled")).toBe(
      true,
    );
    expect(screen.getByLabelText("Nội dung").hasAttribute("disabled")).toBe(
      true,
    );
    expect(
      screen
        .getByRole("button", { name: /Nhân viên/ })
        .hasAttribute("disabled"),
    ).toBe(true);

    finishPreview({ recipientCount: 2 });
    await screen.findByRole("checkbox");
    expect(screen.getByLabelText("Tiêu đề").hasAttribute("disabled")).toBe(
      false,
    );
  });
});
