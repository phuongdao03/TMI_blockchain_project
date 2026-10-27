import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentWorkspace } from "@/components/payments/payment-workspace";

const { cancelMock, getMock, startCheckoutMock } = vi.hoisted(() => ({
  cancelMock: vi.fn(),
  getMock: vi.fn(),
  startCheckoutMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  walletApi: {
    summary: async () => ({
      balanceMinor: 20_000,
      currency: "VND",
      transactions: [],
      topups: [],
      provider: "mock",
    }),
    pay: async (id: string) => ({ id, status: "PAID" }),
  },
  paymentApi: {
    cancel: cancelMock,
    get: getMock,
    startCheckout: startCheckoutMock,
  },
}));

describe("PaymentWorkspace", () => {
  it("describes review intake rather than issuance after submission payment", async () => {
    getMock.mockResolvedValue({
      id: "submission-payment",
      dossierId: "new-dossier",
      orderCode: "123",
      status: "PAID",
      purpose: "SUBMISSION_FEE",
      amountMinor: 5_000_000,
      currency: "VND",
      provider: "wallet",
      paidAt: "2026-10-27T08:00:00Z",
      expiresAt: "2026-11-03T08:00:00Z",
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentWorkspace orderId="submission-payment" />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByText(
        /Hồ sơ đã được tiếp nhận để kiểm tra và thẩm định/,
      ),
    ).toBeDefined();
    expect(screen.queryByText(/đang chuẩn bị và phát hành bằng/)).toBeNull();
  });
  beforeEach(() => {
    getMock.mockReset();
    cancelMock.mockReset();
    startCheckoutMock.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
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

  it("requires explicit wallet confirmation without creating a provider checkout", async () => {
    const user = userEvent.setup();
    const request = {
      id: "payment-request",
      orderCode: "123456",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: null,
      amountMinor: 10_000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-30T08:00:00Z",
      paidAt: null,
      checkoutUrl: null,
      qrPayload: null,
      createdAt: "2026-07-31T08:00:00Z",
      updatedAt: "2026-07-31T08:00:00Z",
    };
    getMock.mockResolvedValue(request);
    startCheckoutMock.mockResolvedValue({
      ...request,
      providerOrderId: "payos-order-123",
      qrPayload: "vietqr-payload",
    });

    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentWorkspace orderId="payment-request" />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("button", { name: /Thanh toán 10/ }),
    ).toBeTruthy();
    expect(startCheckoutMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /Thanh toán 10/ }));

    expect(startCheckoutMock).not.toHaveBeenCalled();
    expect(
      await screen.findByRole("dialog", {
        name: "Xác nhận thanh toán bằng ví",
      }),
    ).toBeTruthy();
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

  it("offers manual status refresh after bounded payment polling", async () => {
    const now = vi.spyOn(Date, "now").mockReturnValue(0);
    getMock.mockResolvedValue({
      id: "payment-pending",
      orderCode: "123458",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: "payos-link-3",
      amountMinor: 10_000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: null,
      checkoutUrl: null,
      qrPayload: null,
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:03:00Z",
    });
    const client = new QueryClient();
    const view = () => (
      <QueryClientProvider client={client}>
        <PaymentWorkspace orderId="payment-pending" />
      </QueryClientProvider>
    );
    const { rerender } = render(view());
    expect(await screen.findByText(/tối đa 5 phút/)).toBeTruthy();

    now.mockReturnValue(300_001);
    rerender(view());
    expect(screen.getByText(/tối đa 5 phút/)).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: "Kiểm tra trạng thái ngay" }),
    );
    expect(getMock).toHaveBeenCalledTimes(2);
  });
  it("shows the payment QR in-page and recovers from an image error on a new order", async () => {
    const pendingOrder = {
      id: "payment-qr",
      orderCode: "123459",
      dossierId: "dossier-1",
      provider: "payos",
      providerOrderId: "provider-order",
      amountMinor: 10_000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: null,
      checkoutUrl: "https://payments.example/checkout",
      qrPayload: "vietqr-payload",
      bankBin: "970422",
      bankAccountNumber: "0123456789",
      bankAccountName: "TINH HOA VIET",
      transferDescription: "CNS 123459",
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:03:00Z",
    };
    getMock.mockResolvedValue(pendingOrder);

    const client = new QueryClient();
    const { rerender } = render(
      <QueryClientProvider client={client}>
        <PaymentWorkspace orderId="payment-qr" />
      </QueryClientProvider>,
    );

    const qr = await screen.findByRole("img", {
      name: "M\u00E3 QR thanh to\u00E1n",
    });
    expect(
      new URL(qr.getAttribute("src")!, window.location.href).pathname,
    ).toBe("/api/v1/payment-orders/payment-qr/qr");
    expect(
      screen.getByText(
        /Qu\u00E9t m\u00E3 b\u1EB1ng \u1EE9ng d\u1EE5ng ng\u00E2n h\u00E0ng/,
      ),
    ).toBeTruthy();
    expect(
      screen.queryByRole("link", { name: /M\u1EDF trang thanh to\u00E1n/ }),
    ).toBeNull();
    expect(screen.getByText("TINH HOA VIET")).toBeTruthy();
    expect(screen.getByText("0123456789")).toBeTruthy();
    expect(screen.getByText("CNS 123459")).toBeTruthy();

    fireEvent.error(qr);
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Không tải được mã QR",
    );
    expect(screen.getByText("0123456789")).toBeTruthy();

    getMock.mockResolvedValue({ ...pendingOrder, id: "payment-qr-2" });
    rerender(
      <QueryClientProvider client={client}>
        <PaymentWorkspace orderId="payment-qr-2" />
      </QueryClientProvider>,
    );
    expect(
      await screen.findByRole("img", { name: "Mã QR thanh toán" }),
    ).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
