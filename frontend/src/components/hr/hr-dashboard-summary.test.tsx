import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HrDashboardSummary } from "@/components/hr/hr-dashboard-summary";

const summary = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  hrDashboardApi: { summary },
}));

const payload = {
  activeEmployeeCount: 8,
  attendancePendingCount: 2,
  locationExceptionPendingCount: 1,
  leavePendingCount: 3,
  overtimePendingCount: 4,
  payrollDraftCount: 1,
  updatedAt: "2026-09-23T08:00:00Z",
};

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("HrDashboardSummary", () => {
  beforeEach(() => {
    summary.mockReset().mockResolvedValue(payload);
  });

  it("links aggregate queues without personal HR information", async () => {
    render(<HrDashboardSummary />, { wrapper: Wrapper });

    const attendance = await screen.findByRole("link", {
      name: /chấm công chờ duyệt/i,
    });
    expect(attendance.getAttribute("href")).toBe("/admin/attendance");
    expect(
      screen
        .getByRole("link", { name: /kỳ lương bản nháp/i })
        .getAttribute("href"),
    ).toBe("/admin/payroll");
    expect(screen.getByText("8")).toBeDefined();
    expect(
      screen.getByText(
        /không hiển thị vị trí, lý do yêu cầu hoặc dữ liệu lương cá nhân/i,
      ),
    ).toBeDefined();
    expect(screen.queryByText("10.776900")).toBeNull();
    expect(screen.queryByText("Pending overtime")).toBeNull();
  });

  it("clearly confirms when no approval queue remains", async () => {
    summary.mockResolvedValueOnce({
      ...payload,
      attendancePendingCount: 0,
      locationExceptionPendingCount: 0,
      leavePendingCount: 0,
      overtimePendingCount: 0,
      payrollDraftCount: 0,
    });
    render(<HrDashboardSummary />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Không có hàng đợi nhân sự cần xử lý."),
    ).toBeDefined();
  });

  it("offers an in-place retry if the summary request fails", async () => {
    const user = userEvent.setup();
    summary
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce(payload);
    render(<HrDashboardSummary />, { wrapper: Wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Thử tải lại hàng đợi" }),
    );
    expect(
      await screen.findByRole("link", { name: /nhân viên đang hoạt động/i }),
    ).toBeDefined();
    expect(summary).toHaveBeenCalledTimes(2);
  });
});
