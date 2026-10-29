import {
  focusManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { LoginVoucher } from "./login-voucher";

const api = vi.hoisted(() => ({ offer: vi.fn(), claim: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ voucherApi: api }));
const offer = {
  id: "campaign-1",
  title: "Tặng bạn 200.000đ",
  description: "Cảm ơn bạn",
  terms: "Không quy đổi thành tiền mặt",
  imagePath: "/images/promotions/golden-voucher.png",
  amountVnd: 200000,
  validityDays: 60,
};
function mount(
  userId: string | null = "owner",
  roles = ["USER"],
  isEmployee = false,
  permissions: string[] = [],
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <LoginVoucher
        userId={userId}
        roles={roles}
        isEmployee={isEmployee}
        permissions={permissions}
      />
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  vi.clearAllMocks();
  sessionStorage.clear();
  api.offer.mockResolvedValue(offer);
  api.claim.mockResolvedValue({
    ...offer,
    id: "claim-1",
    campaignId: offer.id,
    expiresAt: "2026-12-28T00:00:00Z",
  });
});
it("does not request offers for guests", () => {
  mount(null);
  expect(api.offer).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
});
it.each(["promotions.manage", "review.assign", "hr.overtime.create"])(
  "does not request offers for USER accounts with internal permission %s",
  (permission) => {
    mount("manager", ["USER"], false, [permission]);
    expect(api.offer).not.toHaveBeenCalled();
  },
);
it.each<[string[], boolean]>([
  [["SUPER_ADMIN"], false],
  [["USER", "SUPER_ADMIN"], false],
  [["USER", "MODERATOR"], false],
  [["VIEWER"], false],
  [[], false],
  [["USER"], true],
])(
  "does not request offers for excluded account %j / employee %s",
  (roles, isEmployee) => {
    mount("internal-account", roles, isEmployee);
    expect(api.offer).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  },
);
it("claims on click and shows success only after persistence", async () => {
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Nhận voucher ngay" }),
  );
  await screen.findByText("Đã nhận voucher!");
  expect(api.claim).toHaveBeenCalledWith("campaign-1");
  expect(
    screen
      .getByRole("link", { name: "Xem voucher của tôi" })
      .getAttribute("href"),
  ).toBe("/vouchers");
});
it("shows retryable error without claiming success", async () => {
  api.claim.mockRejectedValueOnce(new Error("offline"));
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Nhận voucher ngay" }),
  );
  await screen.findByRole("alert");
  expect(screen.queryByText("Đã nhận voucher!")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Nhận voucher ngay" }));
  await screen.findByText("Đã nhận voucher!");
});
it("dismisses with Escape and remembers dismissal in this tab", async () => {
  const view = mount();
  const dialog = await screen.findByRole("dialog");
  fireEvent.keyDown(dialog, { key: "Escape" });
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  view.unmount();
  mount();
  await waitFor(() => expect(api.offer).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("does not show an offer already claimed on another device", async () => {
  api.offer.mockResolvedValue(null);
  mount();
  await waitFor(() => expect(api.offer).toHaveBeenCalled());
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("prevents repeated clicks while a claim is pending", async () => {
  api.claim.mockReturnValue(new Promise(() => {}));
  mount();
  fireEvent.click(
    await screen.findByRole("button", { name: "Nhận voucher ngay" }),
  );
  const pending = await screen.findByRole("button", {
    name: "Đang nhận voucher…",
  });
  fireEvent.click(pending);
  expect(api.claim).toHaveBeenCalledTimes(1);
});
it("restores focus when dismissed", async () => {
  const trigger = document.createElement("button");
  document.body.appendChild(trigger);
  trigger.focus();
  mount();
  fireEvent.click(await screen.findByRole("button", { name: "Để sau" }));
  await waitFor(() => expect(document.activeElement).toBe(trigger));
  trigger.remove();
});
it("keeps a displayed offer open when the customer returns to the tab", async () => {
  api.offer.mockResolvedValueOnce(offer).mockResolvedValue(null);
  const view = mount();
  await screen.findByRole("dialog");
  try {
    await act(async () => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    expect(api.offer).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("dialog")).toBeDefined();
  } finally {
    view.unmount();
    focusManager.setFocused(undefined);
  }
});
