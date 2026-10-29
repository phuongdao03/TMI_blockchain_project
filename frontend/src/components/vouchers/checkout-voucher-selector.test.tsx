import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CheckoutVoucherSelector } from "./checkout-voucher-selector";
const state = vi.hoisted(() => ({
  request: vi.fn(),
  user: { id: "customer", roles: ["USER"], isEmployee: false },
}));
vi.mock("@/lib/api/client", () => ({ request: state.request }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => state.user }));
function mount(order = false, onSelect = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <CheckoutVoucherSelector
        serviceCode="MEMBERSHIP"
        resourceId="plan"
        order={order}
        onSelect={onSelect}
      />
    </QueryClientProvider>,
  );
  return onSelect;
}
beforeEach(() => {
  state.user = { id: "customer", roles: ["USER"], isEmployee: false };
  state.request
    .mockReset()
    .mockResolvedValue({
      originalVnd: 300000,
      membershipDiscountVnd: 0,
      recommendedVoucherId: "gift",
      vouchers: [
        {
          voucherId: "gift",
          title: "Gift",
          discountVnd: 200000,
          payableVnd: 100000,
        },
      ],
    });
});
it("uses server quote and forwards only the selected voucher identifier", async () => {
  const selected = mount();
  await screen.findByRole("option", { name: /Gift/ });
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "gift" } });
  expect(selected).toHaveBeenCalledWith("gift");
  expect(state.request).toHaveBeenCalledWith("/checkout-vouchers/quote", {
    method: "POST",
    body: JSON.stringify({
      serviceCode: "MEMBERSHIP",
      resourceId: "plan",
      renewalOptIn: false,
    }),
  });
});
it.each([["SUPER_ADMIN"], ["USER", "ADMIN"]])(
  "does not request customer discounts for roles %j",
  (...roles) => {
    state.user.roles = roles;
    mount();
    expect(state.request).not.toHaveBeenCalled();
    expect(screen.queryByRole("combobox")).toBeNull();
  },
);
it("persists payment-order selection and exposes backend rejection", async () => {
  mount(true);
  await screen.findByRole("option", { name: /Gift/ });
  state.request.mockRejectedValueOnce(new Error("Voucher unavailable"));
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "gift" } });
  await waitFor(() =>
    expect(state.request).toHaveBeenCalledWith("/payment-orders/plan/voucher", {
      method: "POST",
      body: JSON.stringify({ voucherId: "gift" }),
    }),
  );
  expect((await screen.findByRole("alert")).textContent).toContain(
    "Voucher unavailable",
  );
});
