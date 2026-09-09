import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OperationsDashboard } from "@/components/admin/operations-dashboard";

const metrics = vi.hoisted(() => vi.fn());

const metricsPayload = {
      dossierFunnel: { UNDER_REVIEW: 4, CERTIFICATE_ISSUED: 2 },
      overdueReviews: 3,
      reviewerWorkload: [
        { reviewerEmail: "reviewer@tmigroup.vn", activeAssignments: 4 },
      ],
      paymentFailures: 1,
      blockchainFailures: 2,
      publicCatalogCacheHitRatio: 0.91,
      publicCatalogCacheOperations: {},
      jobStatusCounts: { QUEUED: 2, DEAD_LETTERED: 1 },
      oldestQueuedJobAgeSeconds: 120,
      jobRetryFailures: 3,
      deadLetteredJobsByTask: { "blockchain.broadcast": 1 },
};

vi.mock("@/lib/api/client", () => ({
  operationsApi: { metrics },
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      {children}
    </QueryClientProvider>
  );
}

describe("OperationsDashboard", () => {
  beforeEach(() => {
    metrics.mockReset().mockResolvedValue(metricsPayload);
  });

  it("presents work queues without raw status, IDs or infrastructure metrics", async () => {
    render(<OperationsDashboard />, { wrapper: Wrapper });

    expect(
      (await screen.findAllByText("Hồ sơ trễ hạn")).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Đang thẩm định")).toBeDefined();
    expect(screen.getByText("reviewer@tmigroup.vn")).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Biểu đồ số hồ sơ theo giai đoạn" }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Biểu đồ cơ cấu cảnh báo vận hành" }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Biểu đồ khối lượng theo chuyên viên" }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Biểu đồ sức khỏe tác vụ nền" }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: "Làm mới dữ liệu" }),
    ).toBeDefined();
    expect(screen.queryByText("UNDER_REVIEW")).toBeNull();
    expect(screen.queryByText(/cache/i)).toBeNull();
    expect(screen.queryByText(/blockchain/i)).toBeNull();
  });

  it("offers an in-place retry when the overview request fails", async () => {
    const user = userEvent.setup();
    metrics
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValueOnce(metricsPayload);

    render(<OperationsDashboard />, { wrapper: Wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Thử tải lại tổng quan" }),
    );
    expect(await screen.findByText("Đang thẩm định")).toBeDefined();
    expect(metrics).toHaveBeenCalledTimes(2);
  });
});
