import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminAttendanceLocationEvidence } from "./admin-attendance-location-evidence";

const listLocationEvidenceMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAdminAttendanceApi: { listLocationEvidence: listLocationEvidenceMock },
}));

describe("AdminAttendanceLocationEvidence", () => {
  beforeEach(() => listLocationEvidenceMock.mockReset());

  it("does not expose expired coordinate values or mount an empty map", async () => {
    listLocationEvidenceMock.mockResolvedValue([
      {
        id: "evidence-1",
        eventType: "CHECK_IN",
        worksitePolicyId: "policy-1",
        worksiteCode: "SGN-HQ",
        worksiteName: "Văn phòng TP. Hồ Chí Minh",
        clientCapturedAt: "2024-01-01T01:00:00Z",
        receivedAt: "2024-01-01T01:00:02Z",
        latitude: null,
        longitude: null,
        accuracyMeters: "12.40",
        distanceMeters: "18.00",
        effectiveTimezone: "Asia/Ho_Chi_Minh",
        permittedRadiusMeters: 250,
        maxAccuracyMeters: 35,
        outcome: "ACCEPTED",
      },
    ]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <AdminAttendanceLocationEvidence
          attendanceId="attendance-1"
          employeeName="Nguyễn Minh Anh"
        />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/Văn phòng TP\. Hồ Chí Minh/)).toBeDefined();
    expect(screen.queryByText("Tọa độ")).toBeNull();
    expect(listLocationEvidenceMock).toHaveBeenCalledWith("attendance-1");
    expect(
      screen.queryByLabelText("Bản đồ vị trí chấm công của nhân viên"),
    ).toBeNull();
  });
});
