import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemberTable } from "@/components/account/member-table";

const members = [
  {
    userId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
    email: "owner@tmigroup.vn",
    roleCode: "OWNER" as const,
    status: "ACTIVE" as const,
    joinedAt: "2026-07-30T08:00:00Z",
  },
  {
    userId: "5f81fa20-ec0a-4393-a90c-bf9c6285766d",
    email: "member@tmigroup.vn",
    roleCode: "MEMBER" as const,
    status: "INVITED" as const,
    joinedAt: null,
  },
];

describe("MemberTable", () => {
  it("shows management actions to an owner or organization manager", () => {
    render(
      <MemberTable
        canManage
        members={members}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        ownerUserId={members[0]!.userId}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Mời thành viên" }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Xóa member@tmigroup.vn" }),
    ).toBeDefined();
    expect(
      screen.queryByRole("button", { name: "Xóa owner@tmigroup.vn" }),
    ).toBeNull();
  });

  it("renders a read-only membership view for regular members", () => {
    render(
      <MemberTable
        canManage={false}
        members={members}
        onAdd={vi.fn()}
        onRemove={vi.fn()}
        ownerUserId={members[0]!.userId}
      />,
    );

    expect(screen.queryByRole("button", { name: "Mời thành viên" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Xóa/ })).toBeNull();
    expect(
      screen.getByText(
        "Chỉ chủ sở hữu hoặc quản lý tổ chức có thể thay đổi thành viên.",
      ),
    ).toBeDefined();
  });
});
