import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { JobOperationsWorkspace } from "@/components/admin/job-operations-workspace";
import { operationsApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  operationsApi: {
    listJobs: vi.fn(),
    replayJob: vi.fn(),
    cancelJob: vi.fn(),
  },
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

describe("JobOperationsWorkspace", () => {
  it("explains failed work and requires a reason before replay", async () => {
    vi.mocked(operationsApi.listJobs).mockResolvedValue({
      success: true,
      data: [
        {
          id: "job-1",
          taskName: "blockchain.broadcast",
          queueName: "blockchain",
          resourceType: "blockchain_transaction",
          resourceId: "tx-1",
          status: "DEAD_LETTERED",
          totalAttempts: 6,
          maxAttempts: 6,
          replayCount: 0,
          version: 7,
          scheduledAt: "2026-08-11T10:00:00Z",
          lastErrorCode: "BLOCKCHAIN_TRANSIENT",
          createdAt: "2026-08-11T10:00:00Z",
          updatedAt: "2026-08-11T10:05:00Z",
        },
      ],
      meta: { request_id: "request-1", page: 1, pageSize: 20, total: 1 },
    });
    vi.mocked(operationsApi.replayJob).mockResolvedValue(undefined as never);

    render(<JobOperationsWorkspace />, { wrapper: Wrapper });

    expect(await screen.findByText("Phát hành chứng thư")).toBeDefined();
    expect(screen.getByText("Cần xử lý")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(screen.getByRole("dialog")).toBeDefined();

    const submit = screen.getByRole("button", { name: "Xác nhận thử lại" });
    expect(submit.getAttribute("disabled")).not.toBeNull();
    fireEvent.change(screen.getByLabelText("Lý do xử lý"), {
      target: { value: "Nhà cung cấp đã hoạt động ổn định" },
    });
    fireEvent.click(submit);

    await waitFor(() =>
      expect(operationsApi.replayJob).toHaveBeenCalledWith("job-1", {
        expectedVersion: 7,
        reason: "Nhà cung cấp đã hoạt động ổn định",
      }),
    );
    expect(
      screen
        .getByText("blockchain.broadcast")
        .closest("details")
        ?.hasAttribute("open"),
    ).toBe(false);
  });
});
