import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";

const issueMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  paymentApi: { issue: issueMock },
}));

describe("PaymentRequestWorkspace", () => {
  it("sends the operator-entered amount instead of a fixed frontend price", async () => {
    issueMock.mockResolvedValue({
      id: "payment-1",
      orderCode: "123456",
      amountMinor: 1_500_000,
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <PaymentRequestWorkspace />
      </QueryClientProvider>,
    );

    fireEvent.change(screen.getByLabelText("Mã hồ sơ"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.change(screen.getByLabelText("Số tiền cần thanh toán (VND)"), {
      target: { value: "1500000" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi yêu cầu thanh toán" }),
    );

    await waitFor(() => expect(issueMock).toHaveBeenCalledOnce());
    expect(issueMock.mock.calls[0]?.[1]).toMatchObject({
      amountMinor: 1_500_000,
      currency: "VND",
      description: "Phí xác lập và phát hành chứng thư",
    });
    expect(
      await screen.findByText("Đã gửi yêu cầu cho người nộp"),
    ).toBeTruthy();
  });
});
