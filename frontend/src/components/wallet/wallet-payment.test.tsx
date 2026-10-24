import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PaymentOrder } from "@/lib/api/types";
import { WalletPayment } from "./wallet-payment";

const api = vi.hoisted(() => ({ summary: vi.fn(), pay: vi.fn() }));
vi.mock("@/lib/api/client", () => ({
  walletApi: api,
  ApiError: class extends Error {},
}));
const order: PaymentOrder = {
  id: "server-order",
  dossierId: "dossier",
  orderCode: "123",
  provider: "payos",
  providerOrderId: null,
  amountMinor: 50_000,
  currency: "VND",
  status: "PENDING",
  expiresAt: "2030-01-01T00:00:00Z",
  paidAt: null,
  checkoutUrl: null,
  qrPayload: null,
  createdAt: "2026-10-22T00:00:00Z",
  updatedAt: "2026-10-22T00:00:00Z",
};

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <WalletPayment order={order} />
    </QueryClientProvider>,
  );
}

describe("wallet payment confirmation", () => {
  beforeEach(() => vi.resetAllMocks());
  it("preserves the dossier destination when the wallet needs funding", async () => {
    api.summary.mockResolvedValue({ balanceMinor: 20_000 });
    mount();
    const link = await screen.findByRole("link", { name: "Nạp tiền vào ví" });
    expect(link.getAttribute("href")).toBe(
      "/wallet?returnTo=%2Fpayments%2Fserver-order",
    );
    expect(api.pay).not.toHaveBeenCalled();
  });
  it("charges only after confirmation using the server order and a stable key", async () => {
    const user = userEvent.setup();
    api.summary.mockResolvedValue({ balanceMinor: 100_000 });
    api.pay.mockResolvedValue({ ...order, status: "PAID" });
    mount();
    await user.click(
      await screen.findByRole("button", { name: /Thanh toán 50/ }),
    );
    expect(api.pay).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Xác nhận thanh toán" }),
    );
    await waitFor(() =>
      expect(api.pay).toHaveBeenCalledWith("server-order", expect.any(String)),
    );
  });
});
