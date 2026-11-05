import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { VoucherWallet } from "./voucher-wallet";

const api = vi.hoisted(() => ({ mine: vi.fn(), redeemCode: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ voucherApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "owner" }),
}));
function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <VoucherWallet />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  api.mine.mockReset();
  api.redeemCode.mockReset();
});
it("shows empty state for an account with no saved vouchers", async () => {
  api.mine.mockResolvedValue([]);
  mount();
  await screen.findByText("Bạn chưa nhận ưu đãi nào.");
});
it("shows persisted value, terms, expiry and server expiry status", async () => {
  api.mine.mockResolvedValue([
    {
      id: "claim",
      title: "Quà tri ân",
      amountVnd: 200000,
      terms: "Không quy đổi thành tiền mặt",
      expiresAt: "2026-12-28T00:00:00Z",
      expired: true,
    },
  ]);
  mount();
  fireEvent.click(await screen.findByRole("tab", { name: /Hết hạn/ }));
  await screen.findByRole("heading", { name: "Quà tri ân" });
  expect(screen.getByText("Đã hết hạn")).toBeDefined();
  expect(screen.getByText("Không quy đổi thành tiền mặt")).toBeDefined();
  expect(document.querySelector("time")?.dateTime).toBe("2026-12-28T00:00:00Z");
});
it("can retry a failed load", async () => {
  api.mine.mockRejectedValueOnce(new Error("offline")).mockResolvedValue([]);
  mount();
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
  await screen.findByText("Bạn chưa nhận ưu đãi nào.");
});

it("keeps an English server error out of the user-facing message", async () => {
  api.mine.mockResolvedValue([]);
  api.redeemCode.mockRejectedValueOnce(new Error("Voucher unavailable"));
  mount();
  fireEvent.change(await screen.findByLabelText("Mã khuyến mại"), {
    target: { value: "GIFT123" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Nhận bằng mã" }));
  await screen.findByText(
    "Không thể nhận ưu đãi bằng mã này. Hãy kiểm tra lại mã và điều kiện áp dụng rồi thử lại.",
  );
  expect(screen.queryByText("Voucher unavailable")).toBeNull();
});
