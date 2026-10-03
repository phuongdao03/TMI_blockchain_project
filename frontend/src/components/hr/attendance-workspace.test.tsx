import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AttendanceWorkspace } from "@/components/hr/attendance-workspace";

const listAttendanceMock = vi.hoisted(() => vi.fn());
const checkInMock = vi.hoisted(() => vi.fn());
const checkOutMock = vi.hoisted(() => vi.fn());
const listLocationEvidenceMock = vi.hoisted(() => vi.fn());
const getWorkdayContextMock = vi.hoisted(() => vi.fn());
const locationMocks = vi.hoisted(() => {
  class LocationCaptureError extends Error {}
  return {
    LocationCaptureError,
    captureForegroundLocation: vi.fn(),
  };
});

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrSelfApi: {
    listAttendance: listAttendanceMock,
    checkIn: checkInMock,
    checkOut: checkOutMock,
    listLocationEvidence: listLocationEvidenceMock,
    getWorkdayContext: getWorkdayContextMock,
  },
}));

vi.mock("@/lib/geolocation", () => locationMocks);

describe("AttendanceWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    locationMocks.captureForegroundLocation.mockResolvedValue({
      latitude: 10.7769,
      longitude: 106.7009,
      accuracyMeters: 18.5,
      clientCapturedAt: "2026-09-21T02:30:00.000Z",
    });
    getWorkdayContextMock.mockResolvedValue({
      workDate: new Date().toISOString().slice(0, 10),
      timezone: "UTC",
    });
  });

  it("does not describe a two-minute attendance as a completed workday", async () => {
    getWorkdayContextMock.mockResolvedValue({
      workDate: "2026-10-03",
      timezone: "Asia/Ho_Chi_Minh",
    });
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "short-attendance",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: "2026-10-03",
          checkInAt: "2026-10-03T10:06:00Z",
          checkOutAt: "2026-10-03T10:08:00Z",
          status: "INCOMPLETE",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2026-10-03T10:06:00Z",
          updatedAt: "2026-10-03T10:08:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Ngày công chưa đủ giờ" }),
    ).toBeDefined();
    expect(screen.getByText("Đã ghi giờ ra · thiếu giờ")).toBeDefined();
    expect(screen.queryByText("Đã hoàn tất ngày công")).toBeNull();
    expect(
      screen.getByText(/Lượt này không tự tính công hoặc lương/),
    ).toBeDefined();
  });

  it("checks in without a note and shows success only after the API accepts it", async () => {
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    checkInMock.mockResolvedValue({ id: "attendance-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    await screen.findByRole("button", { name: "Chấm công vào" });
    expect(
      screen.queryByRole("textbox", { name: /Ghi chú ngày công/i }),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Chấm công vào" }));

    await waitFor(() => {
      expect(checkInMock).toHaveBeenCalledWith({
        latitude: 10.7769,
        longitude: 106.7009,
        accuracyMeters: 18.5,
        clientCapturedAt: "2026-09-21T02:30:00.000Z",
      });
    });
    expect(
      await screen.findByText(
        "Chấm công vào thành công. Thời gian máy chủ và vị trí đã được lưu an toàn.",
      ),
    ).toBeDefined();
    expect(screen.queryByText(/sai số báo cáo/i)).toBeNull();
  });

  it("explains a denied foreground location permission without submitting attendance", async () => {
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    locationMocks.captureForegroundLocation.mockRejectedValue(
      new locationMocks.LocationCaptureError("Bạn đã từ chối quyền vị trí."),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    await screen.findByRole("button", { name: "Chấm công vào" });
    fireEvent.click(screen.getByRole("button", { name: "Chấm công vào" }));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Bạn đã từ chối quyền vị trí.",
    );
    expect(checkInMock).not.toHaveBeenCalled();
  });

  it("sends a new foreground sample when the moderator checks out", async () => {
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-1",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: new Date().toISOString().slice(0, 10),
          checkInAt: "2026-09-21T01:00:00.000Z",
          checkOutAt: null,
          status: "IN_PROGRESS",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2026-09-21T01:00:00.000Z",
          updatedAt: "2026-09-21T01:00:00.000Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    checkOutMock.mockResolvedValue({
      id: "attendance-1",
      status: "INCOMPLETE",
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Chấm công ra" }),
    );

    await waitFor(() => {
      expect(checkOutMock).toHaveBeenCalledWith({
        latitude: 10.7769,
        longitude: 106.7009,
        accuracyMeters: 18.5,
        clientCapturedAt: "2026-09-21T02:30:00.000Z",
      });
    });
    expect(
      await screen.findByText(/Thời gian làm việc chưa đủ để tự tính công/),
    ).toBeDefined();
  });

  it("makes a pending location review explicit and non-payable", async () => {
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-pending",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: new Date().toISOString().slice(0, 10),
          checkInAt: "2026-09-21T01:00:00.000Z",
          checkOutAt: null,
          status: "PENDING",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2026-09-21T01:00:00.000Z",
          updatedAt: "2026-09-21T01:00:00.000Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findAllByText("Chờ duyệt vị trí")).toHaveLength(2);
    expect(
      screen.getByText(/Lượt chấm công này chưa được tính công hoặc lương\./),
    ).toBeDefined();
  });

  it("reveals exact evidence only after the employee explicitly requests it", async () => {
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-evidence",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: new Date().toISOString().slice(0, 10),
          checkInAt: "2026-09-21T01:00:00.000Z",
          checkOutAt: null,
          status: "PRESENT",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2026-09-21T01:00:00.000Z",
          updatedAt: "2026-09-21T01:00:00.000Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    listLocationEvidenceMock.mockResolvedValue([
      {
        id: "evidence-1",
        eventType: "CHECK_IN",
        worksitePolicyId: "policy-1",
        worksiteCode: "SGN-HQ",
        worksiteName: "Ho Chi Minh City HQ",
        clientCapturedAt: "2026-09-21T01:00:00.000Z",
        receivedAt: "2026-09-21T01:00:03.000Z",
        latitude: "10.776900",
        longitude: "106.700900",
        accuracyMeters: "12.50",
        distanceMeters: "0.00",
        effectiveTimezone: "Asia/Ho_Chi_Minh",
        permittedRadiusMeters: 100,
        maxAccuracyMeters: 25,
        outcome: "ACCEPTED",
      },
    ]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("button", { name: "Xem bằng chứng vị trí" }),
    ).toBeDefined();
    expect(screen.queryByText("Ho Chi Minh City HQ")).toBeNull();
    fireEvent.click(
      screen.getByRole("button", { name: "Xem bằng chứng vị trí" }),
    );
    expect(await screen.findByText(/Ho Chi Minh City HQ/)).toBeDefined();
    expect(screen.queryByText("10.776900, 106.700900")).toBeNull();
    expect(screen.queryByText("Tọa độ")).toBeNull();
    expect(listLocationEvidenceMock).toHaveBeenCalledWith(
      "attendance-evidence",
    );
  });

  it("uses the server workday instead of browser UTC to select today's attendance", async () => {
    getWorkdayContextMock.mockResolvedValue({
      workDate: "2001-01-01",
      timezone: "Pacific/Kiritimati",
    });
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-server-day",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: "2001-01-01",
          checkInAt: "2000-12-31T11:30:00.000Z",
          checkOutAt: null,
          status: "PRESENT",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2000-12-31T11:30:00.000Z",
          updatedAt: "2000-12-31T11:30:00.000Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Bạn đang trong ca")).toBeDefined();
    expect(screen.getByText("Ngày công theo Pacific/Kiritimati")).toBeDefined();
    expect(screen.getByRole("button", { name: "Chấm công ra" })).toBeDefined();
    expect(getWorkdayContextMock).toHaveBeenCalledTimes(1);
  });

  it("does not infer a browser workday when the active policy is unavailable", async () => {
    getWorkdayContextMock.mockResolvedValue({
      workDate: null,
      timezone: null,
    });
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(
        /Chưa có địa điểm làm việc và chính sách chấm công hiệu lực/,
      ),
    ).toBeDefined();
    expect(
      screen
        .getByRole("button", { name: "Chưa thể chấm công vào" })
        .hasAttribute("disabled"),
    ).toBe(true);
  });

  it("opens historical evidence only after the employee selects that record", async () => {
    getWorkdayContextMock.mockResolvedValue({
      workDate: "2001-01-02",
      timezone: "Pacific/Kiritimati",
    });
    listAttendanceMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "attendance-history-evidence",
          employeeId: "employee-1",
          employeeName: "Avery Patel",
          workDate: "2001-01-01",
          checkInAt: "2000-12-31T11:30:00.000Z",
          checkOutAt: "2000-12-31T19:30:00.000Z",
          status: "PRESENT",
          lateMinutes: 0,
          earlyLeaveMinutes: 0,
          note: null,
          createdAt: "2000-12-31T11:30:00.000Z",
          updatedAt: "2000-12-31T19:30:00.000Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    listLocationEvidenceMock.mockResolvedValue([
      {
        id: "evidence-history",
        eventType: "CHECK_OUT",
        worksitePolicyId: "policy-1",
        worksiteCode: "KIR-01",
        worksiteName: "Kiritimati Field Site",
        clientCapturedAt: "2000-12-31T19:30:00.000Z",
        receivedAt: "2000-12-31T19:30:03.000Z",
        latitude: "1.872100",
        longitude: "-157.427800",
        accuracyMeters: "12.50",
        distanceMeters: "0.00",
        effectiveTimezone: "Pacific/Kiritimati",
        permittedRadiusMeters: 100,
        maxAccuracyMeters: 25,
        outcome: "ACCEPTED",
      },
    ]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceWorkspace />
      </QueryClientProvider>,
    );

    const evidenceButton = await screen.findByRole("button", {
      name: "Xem bằng chứng vị trí ngày 01/01/2001",
    });
    expect(listLocationEvidenceMock).not.toHaveBeenCalled();
    fireEvent.click(evidenceButton);
    expect(await screen.findByText(/Kiritimati Field Site/)).toBeDefined();
    expect(listLocationEvidenceMock).toHaveBeenCalledWith(
      "attendance-history-evidence",
    );
  });
});
