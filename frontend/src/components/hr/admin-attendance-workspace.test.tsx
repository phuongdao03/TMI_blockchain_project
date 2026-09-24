import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminAttendanceWorkspace } from "@/components/hr/admin-attendance-workspace";

const listAttendanceMock = vi.hoisted(() => vi.fn());
const listLocationExceptionsMock = vi.hoisted(() => vi.fn());
const updateAttendanceMock = vi.hoisted(() => vi.fn());
const listDepartmentsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAdminAttendanceApi: {
    list: listAttendanceMock,
    update: updateAttendanceMock,
    listLocationExceptions: listLocationExceptionsMock,
  },
  hrDepartmentApi: { list: listDepartmentsMock },
}));

describe("AdminAttendanceWorkspace", () => {
  it("submits a confirmed attendance adjustment through the protected client", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    listDepartmentsMock.mockResolvedValue({
      success: true,
      data: [{ id: "department-1", name: "Vận hành" }],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-1",
          employeeId: "employee-1",
          employeeName: "Nguyễn Minh An",
          employeeCode: "OPS-001",
          departmentName: "Vận hành",
          workDate: "2026-09-20",
          checkInAt: "2026-09-20T01:00:00Z",
          checkOutAt: null,
          status: "PRESENT",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2026-09-20T01:00:00Z",
          updatedAt: "2026-09-20T01:00:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    updateAttendanceMock.mockResolvedValue({ id: "attendance-1" });
    listLocationExceptionsMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AdminAttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Nguyễn Minh An")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Điều chỉnh" }));
    fireEvent.change(screen.getByRole("spinbutton", { name: "Phút đi muộn" }), {
      target: { value: "15" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu điều chỉnh" }));

    await waitFor(() => {
      expect(updateAttendanceMock).toHaveBeenCalledWith(
        "attendance-1",
        expect.objectContaining({ lateMinutes: 15, status: "PRESENT" }),
      );
    });
  });
});
