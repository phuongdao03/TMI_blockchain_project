import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentWorkspace } from "@/components/payments/payment-workspace";

const { cancelMock, getMock } = vi.hoisted(() => ({
  cancelMock: vi.fn(),
  getMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: { cancel: cancelMock, get: getMock },
}));

describe("PaymentWorkspace", () => {
  beforeEach(() => {
    getMock.mockReset();
    cancelMock.mockReset();
  });

  it("renders the server-confirmed receipt and never trusts a redirect flag", async () => {
    getMock.mockResolvedValue({
      id: "payment-1",
      orderCode: "PAY-2026-000001",
      dossierId: "dossier-1",
      provider: "mock",
      providerOrderId: "mock-order",
      amountMinor: 1_000_000,
      currency: "VND",
      status: "PAID",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: "2026-08-01T08:03:00Z",
      checkoutUrl: null,
      qrPayload: null,
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:03:00Z",
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentWorkspace orderId="payment-1" />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Thanh toán thành công" }),
    ).toBeTruthy();
    expect(screen.getByText("PAY-2026-000001")).toBeTruthy();
    expect(screen.getByText(/1\.000\.000\s*₫/)).toBeTruthy();
    expect(screen.queryByText(/backend|webhook|blockchain/i)).toBeNull();
  });

  it("shows a user-facing cancelled state without raw provider details", async () => {
    getMock.mockResolvedValue({
      id: "payment-2",
      orderCode: "123456",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: "payos-link-1",
      amountMinor: 10_000,
      currency: "VND",
      status: "CANCELLED",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: null,
      checkoutUrl: null,
      qrPayload: null,
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:03:00Z",
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentWorkspace orderId="payment-2" />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("Bạn đã hủy lần thanh toán này"),
    ).toBeTruthy();
    expect(screen.getByText("Đã hủy")).toBeTruthy();
    expect(screen.queryByText("payos")).toBeNull();
  });

  it("requires a reason before cancelling a pending payOS checkout", async () => {
    const user = userEvent.setup();
    const pendingOrder = {
      id: "payment-3",
      orderCode: "123457",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: "payos-link-2",
      amountMinor: 10_000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: null,
      checkoutUrl: "https://pay.payos.vn/web/payos-link-2",
      qrPayload: "vietqr-payload",
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:03:00Z",
    };
    getMock.mockResolvedValue(pendingOrder);
    cancelMock.mockResolvedValue({ ...pendingOrder, status: "CANCELLED" });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentWorkspace orderId="payment-3" />
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Hủy lần thanh toán" }),
    );
    await user.type(
      screen.getByLabelText("Lý do hủy"),
      "Tôi cần kiểm tra lại hồ sơ",
    );
    await user.click(screen.getByRole("button", { name: "Xác nhận hủy" }));

    expect(cancelMock).toHaveBeenCalledWith(
      "payment-3",
      "Tôi cần kiểm tra lại hồ sơ",
    );
  });
});
