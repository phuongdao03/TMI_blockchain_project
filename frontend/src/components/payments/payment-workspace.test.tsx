import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentWorkspace } from "@/components/payments/payment-workspace";

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  paymentApi: { get: getMock },
}));

describe("PaymentWorkspace", () => {
  beforeEach(() => {
    getMock.mockReset();
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
});
