import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { StaffAccountWorkspace } from "@/components/admin/staff-account-workspace";
import { staffAccountsApi, staffInvitationsApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  staffAccountsApi: {
    list: vi.fn(),
    update: vi.fn(),
    initiateMfaRecovery: vi.fn(),
    requestRoleChange: vi.fn(),
    listPendingActions: vi.fn(),
    approveAction: vi.fn(),
  },
  staffInvitationsApi: {
    list: vi.fn(),
    create: vi.fn(),
    resend: vi.fn(),
    revoke: vi.fn(),
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(staffAccountsApi.list).mockResolvedValue({
    success: true,
    data: [
      {
        id: "staff-1",
        email: "reviewer@tmigroup.vn",
        role: "REVIEWER",
        status: "ACTIVE",
        createdAt: "2026-08-01T00:00:00Z",
        lastLoginAt: null,
      },
      {
        id: "staff-2",
        email: "finance@tmigroup.vn",
        role: "FINANCE_ADMIN",
        status: "SUSPENDED",
        createdAt: "2026-08-02T00:00:00Z",
        lastLoginAt: "2026-08-03T00:00:00Z",
      },
    ],
    meta: { request_id: "staff-list", page: 1, pageSize: 100, total: 2 },
  });
  vi.mocked(staffInvitationsApi.list).mockResolvedValue({
    success: true,
    data: [],
    meta: { request_id: "invite-list", page: 1, pageSize: 20, total: 0 },
  });
  vi.mocked(staffAccountsApi.listPendingActions).mockResolvedValue({
    success: true,
    data: [],
    meta: { request_id: "approval-list", page: 1, pageSize: 50, total: 0 },
  });
  vi.mocked(staffAccountsApi.update).mockResolvedValue({
    id: "staff-1",
    email: "reviewer@tmigroup.vn",
    role: "REVIEWER",
    status: "SUSPENDED",
    createdAt: "2026-08-01T00:00:00Z",
    lastLoginAt: null,
  });
  vi.mocked(staffInvitationsApi.create).mockResolvedValue({
    id: "invite-1",
    email: "new.staff@tmigroup.vn",
    role: "REVIEWER",
    organizationId: null,
    status: "PENDING",
    expiresAt: "2026-08-09T00:00:00Z",
    createdAt: "2026-08-08T00:00:00Z",
  });
  vi.mocked(staffAccountsApi.requestRoleChange).mockResolvedValue({
    id: "action-1",
    targetUserId: "staff-1",
    action: "ROLE_CHANGE",
    status: "PENDING",
    requestedRole: "CONTENT_ADMIN",
    requestedByUserId: "admin-1",
    approvedByUserId: null,
    reason: "Điều chuyển nhiệm vụ đã được xác nhận",
    expiresAt: "2026-08-11T00:00:00Z",
    resolvedAt: null,
  });
});

describe("StaffAccountWorkspace", () => {
  it("shows a clear summary, account table and filters", async () => {
    const user = userEvent.setup();
    render(<StaffAccountWorkspace />, { wrapper });

    expect(await screen.findByText("reviewer@tmigroup.vn")).toBeDefined();
    expect(screen.getAllByText("Đang hoạt động").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Đã khóa").length).toBeGreaterThan(0);
    expect(screen.getByText("2 tài khoản")).toBeDefined();
    expect(screen.getByRole("button", { name: "Gửi lời mời" })).toBeDefined();
    expect(screen.queryByLabelText("Mật khẩu tạm")).toBeNull();

    await user.type(screen.getByRole("searchbox"), "finance");
    await waitFor(() =>
      expect(staffAccountsApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ query: "finance" }),
      ),
    );
  });

  it("requires confirmation before suspending an account", async () => {
    const user = userEvent.setup();
    render(<StaffAccountWorkspace />, { wrapper });
    await screen.findByText("reviewer@tmigroup.vn");

    await user.click(
      screen.getByRole("button", { name: "Khóa reviewer@tmigroup.vn" }),
    );
    expect(staffAccountsApi.update).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Xác nhận trạng thái tài khoản" }),
    ).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Khóa tài khoản" }));
    await waitFor(() =>
      expect(staffAccountsApi.update).toHaveBeenCalledWith("staff-1", {
        status: "SUSPENDED",
      }),
    );
  });

  it("confirms the recipient and task before sending an invitation", async () => {
    const user = userEvent.setup();
    render(<StaffAccountWorkspace />, { wrapper });
    await screen.findByText("reviewer@tmigroup.vn");

    await user.type(
      screen.getByRole("textbox", { name: "Email công việc" }),
      "new.staff@tmigroup.vn",
    );
    await user.click(screen.getByRole("button", { name: "Gửi lời mời" }));
    expect(staffInvitationsApi.create).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Xác nhận mời nhân sự" }),
    ).toBeDefined();

    const confirmationButtons = screen.getAllByRole("button", {
      name: "Gửi lời mời",
    });
    await user.click(confirmationButtons.at(-1)!);
    await waitFor(() =>
      expect(staffInvitationsApi.create).toHaveBeenCalledWith({
        email: "new.staff@tmigroup.vn",
        role: "REVIEWER",
      }),
    );
  });

  it("confirms consequences before changing a staff task", async () => {
    const user = userEvent.setup();
    render(<StaffAccountWorkspace />, { wrapper });
    await screen.findByText("reviewer@tmigroup.vn");

    await user.selectOptions(
      screen.getByLabelText("Nhiệm vụ của reviewer@tmigroup.vn"),
      "CONTENT_ADMIN",
    );
    expect(staffAccountsApi.update).not.toHaveBeenCalled();
    expect(
      screen.getByRole("heading", { name: "Yêu cầu thay đổi nhiệm vụ" }),
    ).toBeDefined();

    await user.type(
      screen.getByRole("textbox", { name: "Căn cứ thay đổi" }),
      "Điều chuyển nhiệm vụ đã được xác nhận",
    );
    await user.click(
      screen.getByRole("button", { name: "Gửi yêu cầu phê duyệt" }),
    );
    await waitFor(() =>
      expect(staffAccountsApi.requestRoleChange).toHaveBeenCalledWith(
        "staff-1",
        "CONTENT_ADMIN",
        "Điều chuyển nhiệm vụ đã được xác nhận",
      ),
    );
  });
});
