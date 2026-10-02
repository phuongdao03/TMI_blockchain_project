import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminAnnouncementWorkspace } from "@/components/admin/admin-announcement-workspace";

const preview = vi.fn();
const send = vi.fn();
vi.mock("@/lib/api/client", () => ({
  adminAnnouncementsApi: {
    preview: (...args: unknown[]) => preview(...args),
    send: (...args: unknown[]) => send(...args),
  },
  adminUsersApi: { list: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

describe("AdminAnnouncementWorkspace", () => {
  beforeEach(() => {
    preview.mockReset();
    send.mockReset();
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
});
