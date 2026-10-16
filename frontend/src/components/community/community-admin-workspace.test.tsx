import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CommunityAdminWorkspace } from "@/components/community/community-admin-workspace";

const auth = vi.hoisted(() => ({
  user: { roles: [] as string[], permissions: [] as string[] },
}));

vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));
vi.mock("@/components/community/community-admin-panels", () => ({
  CommunityCategoryManagement: () => <div>Quản lý danh mục</div>,
  CommunityModerationHistoryPanel: () => <div>Lịch sử kiểm duyệt</div>,
  CommunityReportQueue: () => <div>Hàng báo cáo</div>,
}));
vi.mock("@/components/community/community-admin-content-workspaces", () => ({
  CommunityAdminPostsWorkspace: () => <div>Quản lý bài viết cộng đồng</div>,
  CommunityAdminCommentsWorkspace: () => <div>Quản lý bình luận cộng đồng</div>,
  CommunityAdminMembersWorkspace: () => <div>Quản lý thành viên cộng đồng</div>,
}));

describe("CommunityAdminWorkspace", () => {
  it("preserves moderation tools for community.moderate", () => {
    auth.user = { roles: [], permissions: ["community.moderate"] };
    render(<CommunityAdminWorkspace />);

    expect(screen.getByRole("button", { name: "Báo cáo" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Danh mục" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Bài chờ duyệt" })).toBeNull();
    expect(screen.getByText("Quản lý bài viết cộng đồng")).toBeDefined();
    expect(screen.getByRole("button", { name: "Bài viết" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Bình luận" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Thành viên" })).toBeDefined();
  });

  it("opens each new workspace surface only after selecting its capability-gated tab", async () => {
    const user = userEvent.setup();
    auth.user = { roles: [], permissions: ["community.moderate"] };
    render(<CommunityAdminWorkspace />);

    await user.click(screen.getByRole("button", { name: "Bài viết" }));
    expect(screen.getByText("Quản lý bài viết cộng đồng")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Bình luận" }));
    expect(screen.getByText("Quản lý bình luận cộng đồng")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Thành viên" }));
    expect(screen.getByText("Quản lý thành viên cộng đồng")).toBeDefined();
  });

  it("gives community.manage category tools without moderation access", () => {
    auth.user = { roles: [], permissions: ["community.manage"] };
    render(<CommunityAdminWorkspace />);

    expect(screen.getByRole("button", { name: "Danh mục" })).toBeDefined();
    expect(screen.queryByRole("button", { name: "Cài đặt" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Báo cáo" })).toBeNull();
    expect(screen.queryByText("Hàng chờ duyệt hiện có")).toBeNull();
    expect(screen.getByText("Quản lý danh mục")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Bài viết" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Bình luận" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Thành viên" })).toBeNull();
  });

  it("does not grant workspace access to a generic moderator role", () => {
    auth.user = { roles: ["MODERATOR"], permissions: [] };
    render(<CommunityAdminWorkspace />);

    expect(screen.queryByRole("button", { name: "Báo cáo" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Danh mục" })).toBeNull();
    expect(screen.queryByText("Hàng chờ duyệt hiện có")).toBeNull();
  });
});
