import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ApplicantAccountSummary } from "./applicant-account-summary";

const api = vi.hoisted(() => ({ summary: vi.fn(), unreadCount: vi.fn() }));
vi.mock("@/lib/api/client", () => ({
  walletApi: { summary: api.summary },
  notificationApi: { unreadCount: api.unreadCount },
}));
function mount(owner = "owner-1") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <ApplicantAccountSummary userId={owner} />
    </QueryClientProvider>,
  );
  return { client, ...view };
}
beforeEach(() => {
  vi.resetAllMocks();
  api.summary.mockResolvedValue({ balanceMinor: 0, currency: "VND" });
  api.unreadCount.mockResolvedValue({ unreadCount: 2 });
});

it("shows confirmed zero balance and unread notifications with useful destinations", async () => {
  mount();
  expect(await screen.findByText(/0\s*₫/)).toBeDefined();
  expect(await screen.findByText("2 thông báo chưa đọc")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Mở ví và nạp tiền" })
      .getAttribute("href"),
  ).toBe("/wallet");
  expect(
    screen.getByRole("link", { name: "Xem thông báo" }).getAttribute("href"),
  ).toBe("/notifications");
});
it("keeps failed balance unknown and retries without hiding notification data", async () => {
  api.summary
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ balanceMinor: 250000, currency: "VND" });
  mount();
  await screen.findByText("Chưa tải được số dư.");
  expect(screen.queryByText(/0\s*₫/)).toBeNull();
  expect(await screen.findByText("2 thông báo chưa đọc")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Tải lại số dư" }));
  expect(await screen.findByText(/250\.000\s*₫/)).toBeDefined();
});
it("does not present an unread-count failure as no notifications", async () => {
  api.unreadCount.mockRejectedValue(new Error("offline"));
  mount();
  await screen.findByText("Chưa tải được thông báo.");
  expect(screen.queryByText("Không có thông báo chưa đọc")).toBeNull();
});
it("uses the shared account-scoped balance cache and never shows the previous account", async () => {
  const { client, rerender } = mount();
  await screen.findByText(/0\s*₫/);
  client.setQueryData(["wallet", "owner-1"], {
    balanceMinor: 123000,
    currency: "VND",
  });
  await screen.findByText(/123\.000\s*₫/);
  api.summary.mockImplementation(() => new Promise(() => {}));
  rerender(
    <QueryClientProvider client={client}>
      <ApplicantAccountSummary userId="owner-2" />
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.queryByText(/123\.000\s*₫/)).toBeNull());
  expect(screen.getByText("Đang tải số dư…")).toBeDefined();
});
