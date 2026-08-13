import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CertificateVersionQueue } from "@/components/admin/certificate-version-queue";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  certificateVersionRequestApi: {
    list: listMock,
    decide: vi.fn(),
  },
}));

describe("CertificateVersionQueue", () => {
  it("presents pending work without exposing internal role codes", async () => {
    listMock.mockResolvedValue({
      data: [
        {
          id: "version-2",
          versionNo: 2,
          status: "PENDING_APPROVAL",
          changeReason: "Cập nhật chủ thể theo tài liệu pháp lý mới.",
          requestedAt: "2026-08-11T09:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 50, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <CertificateVersionQueue />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Yêu cầu đang xử lý")).toBeDefined();
    expect(screen.getAllByText("Chờ xem xét").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /Chấp thuận/ })).toBeDefined();
    expect(screen.queryByText("PENDING_APPROVAL")).toBeNull();
    expect(
      screen.queryByText(/SUPER_ADMIN|database|schema|endpoint/i),
    ).toBeNull();
  });
});
