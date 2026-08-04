import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DossierPaymentAction } from "@/components/payments/dossier-payment-action";

const { createMock, pushMock } = vi.hoisted(() => ({
  createMock: vi.fn(),
  pushMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: { create: createMock },
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
      screen.getByRole("button", { name: "Tạo lệnh thanh toán" }),
    );

    await waitFor(() => expect(createMock).toHaveBeenCalledOnce());
    expect(pushMock).toHaveBeenCalledWith("/thanh-toan/payment-1");
  });
});
