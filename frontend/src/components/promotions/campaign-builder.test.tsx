import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { CampaignBuilder } from "./campaign-builder";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/api/client", () => ({
  promotionApi: {
    media: vi
      .fn()
      .mockResolvedValue({ items: [], total: 0, page: 1, pageSize: 20 }),
  },
}));

function mount() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <CampaignBuilder />
    </QueryClientProvider>,
  );
}

it("accepts campaign codes using the browser Unicode-set pattern syntax", () => {
  mount();
  const field = screen.getByRole("textbox", { name: "Mã chiến dịch" });
  const expression = new RegExp(`^(?:${field.getAttribute("pattern")})$`, "v");
  expect(expression.test("EARLY_MEMBER-2026")).toBe(true);
  expect(expression.test("invalid code")).toBe(false);
});

it("lets admins configure percentage discounts and multiple grants per account", () => {
  mount();
  fireEvent.click(screen.getByRole("button", { name: "2. Giá trị" }));
  fireEvent.change(screen.getByRole("combobox", { name: "Loại giảm giá" }), {
    target: { value: "PERCENT" },
  });
  expect(
    screen.getByRole("spinbutton", { name: "Phần trăm giảm (%)" }),
  ).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "6. Giới hạn" }));
  const grants = screen.getByRole("spinbutton", {
    name: "Số voucher mỗi tài khoản",
  });
  fireEvent.change(grants, { target: { value: "3" } });
  expect((grants as HTMLInputElement).value).toBe("3");
});
