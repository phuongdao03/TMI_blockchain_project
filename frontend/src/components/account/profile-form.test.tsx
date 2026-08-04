import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProfileForm } from "@/components/account/profile-form";

describe("ProfileForm", () => {
  it("validates and saves editable profile fields", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <ProfileForm
        onAvatarUploaded={vi.fn()}
        onSave={onSave}
        profile={{
          userId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
          email: "owner@tmigroup.vn",
          fullName: "Nguyễn Minh Anh",
          phone: "+84901234567",
          avatarMediaId: null,
          locale: "vi-VN",
          timezone: "Asia/Ho_Chi_Minh",
        }}
      />,
    );

    await user.clear(screen.getByLabelText("Họ và tên"));
    await user.type(screen.getByLabelText("Họ và tên"), "Nguyễn An");
    await user.click(screen.getByRole("button", { name: "Lưu hồ sơ" }));

    expect(onSave).toHaveBeenCalledWith({
      fullName: "Nguyễn An",
      phone: "+84901234567",
      locale: "vi-VN",
      timezone: "Asia/Ho_Chi_Minh",
    });
  });

  it("shows the current avatar state with the secure uploader", () => {
    render(
      <ProfileForm
        onAvatarUploaded={vi.fn()}
        onSave={vi.fn()}
        profile={{
          userId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
          email: "owner@tmigroup.vn",
          fullName: null,
          phone: null,
          avatarMediaId: null,
          locale: "vi-VN",
          timezone: "Asia/Ho_Chi_Minh",
        }}
      />,
    );

    expect(screen.getByText("Chưa có ảnh đại diện")).toBeDefined();
    expect(screen.getByLabelText("Chọn ảnh đại diện")).toBeDefined();
    expect(screen.getByRole("button", { name: "Chọn tệp" })).toBeDefined();
  });
});
