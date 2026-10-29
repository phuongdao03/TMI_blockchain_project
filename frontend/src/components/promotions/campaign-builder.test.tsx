import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { CampaignBuilder } from "./campaign-builder";
import { newCampaign } from "@/lib/api/promotion-types";

const api = vi.hoisted(() => ({ detail: vi.fn(), update: vi.fn() }));
beforeEach(() => vi.clearAllMocks());

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }) }));
vi.mock("@/lib/api/client", () => ({
  promotionApi: {
    ...api,
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

it("lets admins edit an active campaign and save a new policy version", async () => {
  const campaign = {
    ...newCampaign(),
    id: "live",
    status: "ACTIVE",
    name: "Live campaign",
    code: "LIVE",
    title: "Gift",
    description: "Gift details",
    policyVersion: 1,
  };
  api.detail.mockResolvedValue(campaign);
  api.update.mockResolvedValue({
    ...campaign,
    name: "Updated campaign",
    policyVersion: 2,
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CampaignBuilder id="live" />
    </QueryClientProvider>,
  );
  const name = await screen.findByRole("textbox", { name: "Tên chiến dịch" });
  expect(name.closest("fieldset")?.disabled).toBe(false);
  fireEvent.change(name, { target: { value: "Updated campaign" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
  await screen.findByText("Đã lưu chiến dịch.");
  expect(api.update).toHaveBeenCalledWith(
    "live",
    expect.objectContaining({ name: "Updated campaign" }),
  );
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

it("explains account creation dates and rejects an empty audience interval", () => {
  mount();
  fireEvent.click(screen.getByRole("button", { name: "4. Đối tượng" }));
  const before = screen.getByLabelText("Tài khoản được tạo trước");
  const after = screen.getByLabelText("Tài khoản được tạo từ");
  fireEvent.change(before, { target: { value: "2026-08-01T22:03" } });
  fireEvent.change(after, { target: { value: "2026-08-01T22:03" } });
  expect(screen.getByRole("alert").textContent).toContain("không hợp lệ");
  expect(
    (screen.getByRole("button", { name: "Lưu nháp" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
