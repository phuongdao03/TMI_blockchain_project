import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DossierPaymentAction } from "@/components/payments/dossier-payment-action";

const { createMock, getActiveMock, pushMock } = vi.hoisted(() => ({
  createMock: vi.fn(),
  getActiveMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: { create: createMock, getActive: getActiveMock },
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe("DossierPaymentAction", () => {
  it("creates an idempotent order and opens its status page", async () => {
    createMock.mockResolvedValue({ id: "payment-1" });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierPaymentAction dossierId="dossier-1" dossierStatus="APPROVED" />
      </QueryClientProvider>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Thanh toán phí phát hành" }),
    );

    await waitFor(() => expect(createMock).toHaveBeenCalledOnce());
    expect(pushMock).toHaveBeenCalledWith("/payments/payment-1");
  });

  it("resumes the active payment after an interrupted checkout", async () => {
    getActiveMock.mockResolvedValue({ id: "payment-active" });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierPaymentAction
          dossierId="dossier-1"
          dossierStatus="PAYMENT_PENDING"
        />
      </QueryClientProvider>,
    );

    expect(
      (
        await screen.findByRole("link", { name: "Mở lại trang thanh toán" })
      ).getAttribute("href"),
    ).toBe("/payments/payment-active");
  });
});
