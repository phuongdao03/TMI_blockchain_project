import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { OperationsDashboard } from "@/components/admin/operations-dashboard";
import { ApiError } from "@/lib/api/client";

const metrics = vi.hoisted(() => vi.fn());
const listReviewDossiers = vi.hoisted(() => vi.fn());

const metricsPayload = {
  dossierFunnel: { UNDER_REVIEW: 4, CERTIFICATE_ISSUED: 2 },
  overdueReviews: 3,
  reviewerWorkload: [
    { reviewerEmail: "reviewer@cnsgroup.vn", activeAssignments: 4 },
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
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      readonly code: string,
      readonly status: number,
      readonly requestId?: string,
    ) {
      super(message);
    }
  },
  operationsApi: { metrics },
  adminReviewApi: { list: listReviewDossiers },
}));

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

describe("OperationsDashboard", () => {
  beforeEach(() => {
    metrics.mockReset().mockResolvedValue(metricsPayload);
    listReviewDossiers.mockReset().mockResolvedValue({
      data: [],
      meta: { total: 3 },
    });
  });

  it("presents work queues without raw status, IDs or infrastructure metrics", async () => {
    render(<OperationsDashboard />, { wrapper: Wrapper });

    expect(
      (await screen.findAllByText("Hồ sơ trễ hạn")).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Đang thẩm định")).toBeDefined();
    expect(screen.getByText("reviewer@cnsgroup.vn")).toBeDefined();
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

  it("links real dossier stage counts to the matching admin queue filter", async () => {
    metrics.mockResolvedValue({
      ...metricsPayload,
      dossierFunnel: { SUBMITTED: 3, PRECHECK: 2, UNDER_REVIEW: 4 },
    });
    render(<OperationsDashboard showHeader={false} />, { wrapper: Wrapper });

    const stageCounts = await screen.findByRole("region", {
      name: "Số hồ sơ theo bước xử lý",
    });
    expect(stageCounts.textContent).toContain("Đã nộp3");
    expect(
      screen
        .getByRole("link", { name: "Đã nộp: 3 hồ sơ" })
        .getAttribute("href"),
    ).toBe("/admin/reviews?status=SUBMITTED");
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

  it("shows the request ID when production metrics fail", async () => {
    metrics.mockRejectedValueOnce(
      new ApiError("unavailable", "OPERATIONS_UNAVAILABLE", 503, "req-42"),
    );
    render(<OperationsDashboard />, { wrapper: Wrapper });
    expect(
      await screen.findByText(/OPERATIONS_UNAVAILABLE · Mã yêu cầu: req-42/),
    ).toBeDefined();
    expect(
      await screen.findByText("3 hồ sơ đang chờ kiểm tra hoặc thẩm định."),
    ).toBeDefined();
    expect(
      screen.getByRole("link", { name: "Xem hồ sơ chờ xử lý" }),
    ).toBeDefined();
  });
});
