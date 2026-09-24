import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminOvertimeWorkspace } from "@/components/hr/admin-overtime-workspace";

const listMock = vi.hoisted(() => vi.fn());
const decideMock = vi.hoisted(() => vi.fn());
const departmentsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAdminOvertimeApi: { list: listMock, decide: decideMock },
  hrDepartmentApi: { list: departmentsMock },
}));

describe("AdminOvertimeWorkspace", () => {
  it("confirms approval before deciding a pending request", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    departmentsMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { page: 1, pageSize: 100, total: 0 },
    });
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "overtime-1",
          employeeId: "employee-1",
          employeeName: "Nguyễn Minh An",
          employeeCode: "OPS-001",
          departmentName: "Vận hành",
          startAt: "2026-09-24T17:00:00Z",
          endAt: "2026-09-24T20:00:00Z",
          reason: "Hỗ trợ sự cố",
          status: "PENDING",
          decisionNote: null,
          reviewedByUserId: null,
          reviewedAt: null,
          createdAt: "2026-09-20T01:00:00Z",
          updatedAt: "2026-09-20T01:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 100, total: 1 },
    });
    decideMock.mockResolvedValue({ id: "overtime-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AdminOvertimeWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Nguyễn Minh An")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Duyệt" }));
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận duyệt" }));
    await waitFor(() =>
      expect(decideMock).toHaveBeenCalledWith("overtime-1", "approve", {
        decisionNote: null,
      }),
    );
  });
});
