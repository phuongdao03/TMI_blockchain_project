import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OvertimeWorkspace } from "@/components/hr/overtime-workspace";

const listMock = vi.hoisted(() => vi.fn());
const createMock = vi.hoisted(() => vi.fn());
const cancelMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrSelfApi: {
    listOvertimeRequests: listMock,
    createOvertimeRequest: createMock,
    cancelOvertimeRequest: cancelMock,
  },
}));

describe("OvertimeWorkspace", () => {
  it("submits a timezone-aware overtime interval", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
    });
    createMock.mockResolvedValue({ id: "overtime-1" });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <OvertimeWorkspace />
      </QueryClientProvider>,
    );

    fireEvent.change(await screen.findByLabelText("Bắt đầu"), {
      target: { value: "2026-09-24T17:00" },
    });
    fireEvent.change(screen.getByLabelText("Kết thúc"), {
      target: { value: "2026-09-24T20:00" },
    });
    fireEvent.change(screen.getByLabelText("Lý do tăng ca"), {
      target: { value: "Hỗ trợ sự cố" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi yêu cầu tăng ca" }),
    );

    await waitFor(() =>
      expect(createMock).toHaveBeenCalledWith({
        startAt: "2026-09-24T10:00:00.000Z",
        endAt: "2026-09-24T13:00:00.000Z",
        reason: "Hỗ trợ sự cố",
      }),
    );
  });
});
