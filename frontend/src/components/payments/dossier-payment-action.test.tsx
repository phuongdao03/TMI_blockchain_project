import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DossierPaymentAction } from "@/components/payments/dossier-payment-action";

const getActiveMock = vi.hoisted(() => vi.fn());
const getFeeObligationMock = vi.hoisted(() => vi.fn());
const createCheckoutMock = vi.hoisted(() => vi.fn());
const pushMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: pushMock }) }));

vi.mock("@/lib/api/client", () => ({
  paymentApi: {
    createCheckout: createCheckoutMock,
    getActive: getActiveMock,
    getFeeObligation: getFeeObligationMock,
  },
}));

function renderAction(status: "APPROVED" | "PAYMENT_PENDING") {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <DossierPaymentAction dossierId="dossier-1" dossierStatus={status} />
    </QueryClientProvider>,
  );
}

describe("DossierPaymentAction", () => {
  it("does not let an applicant choose or create a payment amount", () => {
    renderAction("APPROVED");

    expect(screen.getByText("Hồ sơ đã được phê duyệt")).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
    expect(getActiveMock).not.toHaveBeenCalled();
  });

  it("shows the exact admin-issued amount and opens PayOS status", async () => {
    getActiveMock.mockResolvedValue({
      id: "payment-active",
      amountMinor: 1_500_000,
      description: "Phí xác lập và phát hành chứng thư",
    });
    renderAction("PAYMENT_PENDING");

    expect(await screen.findByText(/1\.500\.000 VND/)).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Xem và thanh toán qua PayOS" })
        .getAttribute("href"),
    ).toBe("/payments/payment-active");
  });

  it("creates a short-lived PayOS checkout from the locked listed price", async () => {
    const user = userEvent.setup();
    getActiveMock.mockRejectedValueOnce(new Error("No active checkout"));
    getFeeObligationMock.mockResolvedValueOnce({
      id: "obligation-1",
      amountMinor: 1_750_000,
      currency: "VND",
      description: "Phí xác lập và phát hành chứng thư",
      dueAt: "2026-09-06T10:00:00Z",
    });
    createCheckoutMock.mockResolvedValueOnce({ id: "checkout-1" });

    renderAction("PAYMENT_PENDING");

    const button = await screen.findByRole("button", {
      name: "Thanh toán qua PayOS",
    });
    expect(screen.getByText(/1\.750\.000/)).toBeTruthy();
    await user.click(button);

    expect(createCheckoutMock).toHaveBeenCalledWith(
      "obligation-1",
      expect.any(String),
    );
    expect(pushMock).toHaveBeenCalledWith("/payments/checkout-1");
  });
});
