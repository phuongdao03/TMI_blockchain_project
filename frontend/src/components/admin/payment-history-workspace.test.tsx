import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentHistoryWorkspace } from "@/components/admin/payment-history-workspace";

const { detailMock, exportMock, listMock } = vi.hoisted(() => ({
  detailMock: vi.fn(),
  exportMock: vi.fn(),
  listMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: {
    listHistory: listMock,
    getAdminHistoryDetail: detailMock,
    exportHistory: exportMock,
  },
}));

vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({
    roles: ["SUPER_ADMIN"],
    permissions: ["payments.export"],
  }),
}));

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <PaymentHistoryWorkspace />
    </QueryClientProvider>,
  );
}

describe("PaymentHistoryWorkspace", () => {
  beforeEach(() => {
    listMock.mockReset();
    detailMock.mockReset();
    exportMock.mockReset();
    listMock.mockResolvedValue({
      data: {
        rows: [
          {
            order: {
              id: "order-1",
              orderCode: "12345",
              amountMinor: 125000,
              currency: "VND",
              status: "PAID",
              createdAt: "2026-10-01T08:00:00Z",
              paidAt: "2026-10-01T08:05:00Z",
              dueAt: null,
              description: "Phí xác lập",
            },
            dossierCode: "THV-001",
            dossierTitle: "Hồ sơ di sản",
            applicantUserId: "applicant-1",
            applicantEmail: "owner@example.vn",
            initiatedByEmail: "staff@example.vn",
          },
        ],
        summary: {
          total: 1,
          statusCounts: { PAID: 1 },
          totalAmountMinor: 125000,
          paidAmountMinor: 125000,
        },
      },
      meta: { page: 1, pageSize: 25, total: 1 },
    });
    detailMock.mockResolvedValue({
      row: {
        order: { description: "Phí xác lập", dueAt: null },
        applicantEmail: "owner@example.vn",
        initiatedByEmail: "staff@example.vn",
      },
      statusHistory: [
        {
          id: "history-1",
          fromStatus: null,
          toStatus: "PROCESSING",
          source: "ORDER_CREATED",
          actorEmail: "staff@example.vn",
          changedAt: "2026-10-01T08:00:00Z",
        },
      ],
    });
  });

  it("shows payer and initiator separately and reveals status history", async () => {
    renderWorkspace();
    await screen.findByText("THV-001 · Hồ sơ di sản");
    expect(screen.getByText(/owner@example\.vn/)).toBeDefined();
    expect(screen.getByText(/staff@example\.vn/)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Chi tiết" }));
    expect(await screen.findByText("Lịch sử trạng thái")).toBeDefined();
    expect(screen.getByText("Khởi tạo → Đang xác nhận")).toBeDefined();
  });

  it("passes status and search terms to the server when filtering", async () => {
    renderWorkspace();
    await screen.findByText("THV-001 · Hồ sơ di sản");
    fireEvent.change(
      screen.getByPlaceholderText("Mã giao dịch, hồ sơ hoặc email"),
      {
        target: { value: "owner@example.vn" },
      },
    );
    fireEvent.change(screen.getByLabelText("Trạng thái"), {
      target: { value: "PAID" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lọc" }));
    expect(await screen.findByText("THV-001 · Hồ sơ di sản")).toBeDefined();
    expect(listMock).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "owner@example.vn", status: "PAID" }),
    );
  });
});
