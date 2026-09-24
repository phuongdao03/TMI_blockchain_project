import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminLeaveWorkspace } from "@/components/hr/admin-leave-workspace";

const listLeaveRequestsMock = vi.hoisted(() => vi.fn());
const decideLeaveRequestMock = vi.hoisted(() => vi.fn());
const listDepartmentsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAdminLeaveApi: {
    list: listLeaveRequestsMock,
    decide: decideLeaveRequestMock,
  },
  hrDepartmentApi: { list: listDepartmentsMock },
}));

describe("AdminLeaveWorkspace", () => {
  it("approves a pending leave request after explicit confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    listDepartmentsMock.mockResolvedValue({
      success: true,
      data: [{ id: "department-1", name: "Vận hành" }],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    listLeaveRequestsMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "leave-1",
          employeeId: "employee-1",
          employeeName: "Nguyễn Minh An",
          employeeCode: "OPS-001",
          departmentName: "Vận hành",
          leaveType: "Nghỉ phép năm",
          startDate: "2026-09-24",
          endDate: "2026-09-25",
          reason: "Việc gia đình",
          status: "PENDING",
          decisionNote: null,
          reviewedByUserId: null,
          reviewedAt: null,
          createdAt: "2026-09-20T01:00:00Z",
          updatedAt: "2026-09-20T01:00:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    decideLeaveRequestMock.mockResolvedValue({ id: "leave-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AdminLeaveWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Nguyễn Minh An")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Duyệt" }));
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận duyệt" }));

    await waitFor(() => {
      expect(decideLeaveRequestMock).toHaveBeenCalledWith(
        "leave-1",
        "approve",
        { decisionNote: null },
      );
    });
  });
});
