import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PayrollWorkspace } from "@/components/hr/payroll-workspace";

const listPeriodsMock = vi.hoisted(() => vi.fn());
const getPeriodMock = vi.hoisted(() => vi.fn());
const recalculateMock = vi.hoisted(() => vi.fn());
const listWorksitesMock = vi.hoisted(() => vi.fn());
const exportPayrollMock = vi.hoisted(() => vi.fn());
const saveWorkbookMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/download", () => ({ saveWorkbook: saveWorkbookMock }));

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAttendanceConfigurationApi: { listWorksites: listWorksitesMock },
  hrPayrollApi: {
    listPeriods: listPeriodsMock,
    getPeriod: getPeriodMock,
    recalculate: recalculateMock,
    exportXlsx: exportPayrollMock,
    createPeriod: vi.fn(),
    updateEntry: vi.fn(),
    confirmPeriod: vi.fn(),
    markPaid: vi.fn(),
  },
}));

const period = {
  id: "period-1",
  worksiteId: "worksite-1",
  periodMonth: "2026-09-01",
  currency: "VND",
  standardWorkdays: 22,
  status: "DRAFT" as const,
  calculatedAt: "2026-09-20T03:00:00Z",
  confirmedAt: null,
  confirmedByUserId: null,
  paidAt: null,
  paidByUserId: null,
  createdAt: "2026-09-01T00:00:00Z",
  updatedAt: "2026-09-20T03:00:00Z",
};

describe("PayrollWorkspace", () => {
  it("shows VND payroll data and recalculates a draft without location evidence", async () => {
    listWorksitesMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "worksite-1",
          code: "HCM",
          name: "Văn phòng TP. Hồ Chí Minh",
          status: "ACTIVE",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    listPeriodsMock.mockResolvedValue({
      success: true,
      data: [period],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    getPeriodMock.mockResolvedValue({
      ...period,
      entries: [
        {
          id: "entry-1",
          payrollPeriodId: "period-1",
          employeeId: "employee-1",
          employeeCode: "OPS-001",
          employeeName: "Nguyễn Minh An",
          baseSalary: "18000000",
          attendanceWorkdays: "20.5",
          approvedOvertimeHours: "8",
          allowance: "2000000",
          socialInsurance: "1890000",
          incomeTax: "700000",
          dailySalary: "818182",
          overtimeSalary: "1227273",
          grossPay: "20000004",
          totalDeductions: "2590000",
          netPay: "17410004",
          createdAt: "2026-09-20T03:00:00Z",
          updatedAt: "2026-09-20T03:00:00Z",
        },
      ],
    });
    recalculateMock.mockResolvedValue([]);
    exportPayrollMock.mockResolvedValue(new Blob(["xlsx"]));
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <PayrollWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findAllByText("Nguyễn Minh An")).toHaveLength(2);
    expect(screen.getAllByText(/17\.410\.004/)).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Xuất Excel" }));
    await waitFor(() => {
      expect(exportPayrollMock).toHaveBeenCalledWith("period-1");
      expect(saveWorkbookMock).toHaveBeenCalledWith(
        expect.any(Blob),
        "hr-payroll.xlsx",
      );
    });
    expect(screen.queryByText(/tọa độ|lý do tăng ca/i)).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Tính lại số liệu" }));

    await waitFor(() => {
      expect(recalculateMock).toHaveBeenCalledWith(
        "period-1",
        expect.anything(),
      );
    });
    expect(
      await screen.findByText("Đã cập nhật số liệu kỳ lương."),
    ).toBeDefined();
  });
});
