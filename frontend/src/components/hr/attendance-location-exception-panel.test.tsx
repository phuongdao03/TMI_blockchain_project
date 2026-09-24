import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AttendanceLocationExceptionPanel } from "@/components/hr/attendance-location-exception-panel";

const listLocationExceptionsMock = vi.hoisted(() => vi.fn());
const decideLocationExceptionMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAdminAttendanceApi: {
    listLocationExceptions: listLocationExceptionsMock,
    decideLocationException: decideLocationExceptionMock,
  },
}));

describe("AttendanceLocationExceptionPanel", () => {
  it("requires a reason before a super admin approves exact location evidence", async () => {
    listLocationExceptionsMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "exception-1",
          attendanceId: "attendance-1",
          locationEvidenceId: "evidence-1",
          status: "PENDING",
          requestedByUserId: "user-1",
          decisionNote: null,
          reviewedByUserId: null,
          reviewedAt: null,
          createdAt: "2026-09-21T01:00:00.000Z",
          updatedAt: "2026-09-21T01:00:00.000Z",
          employeeId: "employee-1",
          employeeCode: "OPS-001",
          employeeName: "Avery Patel",
          workDate: "2026-09-21",
          attendanceStatus: "PENDING",
          evidence: {
            id: "evidence-1",
            eventType: "CHECK_IN",
            worksitePolicyId: "policy-1",
            worksiteCode: "SGN-HQ",
            worksiteName: "Ho Chi Minh City HQ",
            clientCapturedAt: "2026-09-21T01:00:00.000Z",
            receivedAt: "2026-09-21T01:00:03.000Z",
            latitude: "10.786900",
            longitude: "106.700900",
            accuracyMeters: "12.50",
            distanceMeters: "1111.95",
            effectiveTimezone: "Asia/Ho_Chi_Minh",
            permittedRadiusMeters: 100,
            maxAccuracyMeters: 25,
            outcome: "OUTSIDE_WORKSITE",
          },
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    decideLocationExceptionMock.mockResolvedValue({ id: "exception-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <AttendanceLocationExceptionPanel />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Avery Patel")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Duyệt vị trí" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Nhập lý do gồm ít nhất 2 ký tự.",
    );

    fireEvent.change(screen.getByLabelText("Lý do quyết định"), {
      target: { value: "Verified field assignment." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Duyệt vị trí" }));
    await waitFor(() => {
      expect(decideLocationExceptionMock).toHaveBeenCalledWith("exception-1", {
        status: "APPROVED",
        decisionNote: "Verified field assignment.",
      });
    });
  });
});
