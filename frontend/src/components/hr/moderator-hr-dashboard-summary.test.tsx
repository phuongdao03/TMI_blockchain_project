import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ModeratorHrDashboardSummary } from "@/components/hr/moderator-hr-dashboard-summary";

const summary = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  hrModeratorDashboardApi: { summary },
}));

const payload = {
  profileLinked: true,
  workDate: "2026-09-23",
  timezone: "Asia/Ho_Chi_Minh",
  attendanceStatus: "PENDING" as const,
  checkInAt: "2026-09-23T01:00:00Z",
  checkOutAt: null,
  leavePendingCount: 2,
  overtimePendingCount: 1,
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

describe("ModeratorHrDashboardSummary", () => {
  beforeEach(() => {
    summary.mockReset().mockResolvedValue(payload);
  });

  it("presents only personal HR actions with the server-owned local workday", async () => {
    render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Chấm công đang chờ xác minh"),
    ).toBeDefined();
    expect(
      screen.getByText(/ngày làm việc 2026-09-23 theo asia\/ho_chi_minh/i),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: /yêu cầu nghỉ phép đang chờ/i })
        .getAttribute("href"),
    ).toBe("/leave");
    expect(screen.queryByText("10.776900")).toBeNull();
    expect(screen.queryByText("Personal overtime")).toBeNull();
  });

  it("explains the safe no-profile state", async () => {
    summary.mockResolvedValueOnce({
      ...payload,
      profileLinked: false,
      workDate: null,
      timezone: null,
      attendanceStatus: null,
      checkInAt: null,
      leavePendingCount: 0,
      overtimePendingCount: 0,
    });
    render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

    expect(
      await screen.findByText("Chưa liên kết hồ sơ nhân sự"),
    ).toBeDefined();
    expect(screen.queryByRole("link", { name: /mở chấm công/i })).toBeNull();
  });

  it.each([
    ["LEAVE", "Đã ghi nhận nghỉ phép"],
    ["ABSENT", "Đã ghi nhận vắng mặt"],
    ["HALF_DAY", "Đã ghi nhận nửa ngày công"],
    ["PRESENT", "Đã có bản ghi chấm công"],
  ] as const)(
    "does not invent a check-in for %s without timestamps",
    async (status, title) => {
      summary.mockResolvedValueOnce({
        ...payload,
        attendanceStatus: status,
        checkInAt: null,
      });
      render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

      expect(await screen.findByText(title)).toBeDefined();
      expect(screen.queryByText("Đã ghi nhận giờ vào")).toBeNull();
    },
  );

  it("shows the configured worksite time rather than the browser timezone", async () => {
    summary.mockResolvedValueOnce({ ...payload, attendanceStatus: "PRESENT" });
    render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

    expect(await screen.findByText("Đã ghi nhận giờ vào")).toBeDefined();
    expect(screen.getByText(/Giờ vào: 08:00/)).toBeDefined();
    expect(screen.getByText(/Giờ ra: Chưa ghi nhận/)).toBeDefined();
  });

  it("keeps leave and overtime accessible when the worksite is not configured", async () => {
    summary.mockResolvedValueOnce({
      ...payload,
      workDate: null,
      timezone: null,
      attendanceStatus: null,
      checkInAt: null,
    });
    render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

    expect(await screen.findByText("Chưa có lịch làm việc")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: /yêu cầu tăng ca đang chờ/i })
        .getAttribute("href"),
    ).toBe("/overtime");
    expect(screen.queryByText("Chưa chấm công")).toBeNull();
  });

  it("offers a retry if the personal summary request fails", async () => {
    const user = userEvent.setup();
    summary
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce(payload);
    render(<ModeratorHrDashboardSummary />, { wrapper: Wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Thử tải lại" }),
    );
    expect(
      await screen.findByText("Chấm công đang chờ xác minh"),
    ).toBeDefined();
    expect(summary).toHaveBeenCalledTimes(2);
  });
});
