import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PaymentReturnWorkspace } from "@/components/payments/payment-return-workspace";

const { getByProviderReferenceMock, getMock } = vi.hoisted(() => ({
  getByProviderReferenceMock: vi.fn(),
  getMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: {
    getByProviderReference: getByProviderReferenceMock,
    get: getMock,
  },
}));

describe("PaymentReturnWorkspace", () => {
  it("uses the verified server state instead of browser return status", async () => {
    const pendingOrder = {
      id: "payment-1",
      orderCode: "123456",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: "payos-link-1",
      amountMinor: 10_000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-08T08:15:00Z",
      paidAt: null,
      checkoutUrl: "https://pay.payos.vn/web/payos-link-1",
      qrPayload: "vietqr-payload",
      createdAt: "2026-08-08T08:00:00Z",
      updatedAt: "2026-08-08T08:00:00Z",
    };
    getByProviderReferenceMock.mockResolvedValue(pendingOrder);
    getMock.mockResolvedValue(pendingOrder);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentReturnWorkspace providerOrderId="payos-link-1" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Đang chờ xác nhận")).toBeTruthy();
    expect(screen.queryByText("Thanh toán thành công")).toBeNull();
    expect(getByProviderReferenceMock).toHaveBeenCalledWith("payos-link-1");
  });
});
