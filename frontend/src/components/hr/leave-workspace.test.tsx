import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LeaveWorkspace } from "@/components/hr/leave-workspace";

const listLeaveRequestsMock = vi.hoisted(() => vi.fn());
const createLeaveRequestMock = vi.hoisted(() => vi.fn());
const cancelLeaveRequestMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrSelfApi: {
    listLeaveRequests: listLeaveRequestsMock,
    createLeaveRequest: createLeaveRequestMock,
    cancelLeaveRequest: cancelLeaveRequestMock,
  },
}));

describe("LeaveWorkspace", () => {
  it("submits a validated personal leave request through the protected client", async () => {
    listLeaveRequestsMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    createLeaveRequestMock.mockResolvedValue({ id: "leave-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <LeaveWorkspace />
      </QueryClientProvider>,
    );

    fireEvent.change(await screen.findByLabelText("Loại nghỉ"), {
      target: { value: "Nghỉ phép năm" },
    });
    fireEvent.change(screen.getByLabelText("Từ ngày"), {
      target: { value: "2026-09-24" },
    });
    fireEvent.change(screen.getByLabelText("Đến ngày"), {
      target: { value: "2026-09-25" },
    });
    fireEvent.change(screen.getByLabelText("Lý do"), {
      target: { value: "Việc gia đình" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Gửi đơn nghỉ" }));

    await waitFor(() => {
      expect(createLeaveRequestMock).toHaveBeenCalledWith({
        leaveType: "Nghỉ phép năm",
        startDate: "2026-09-24",
        endDate: "2026-09-25",
        reason: "Việc gia đình",
      });
    });
  });
});
