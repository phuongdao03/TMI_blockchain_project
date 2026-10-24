import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AdminEventsWorkspace } from "./admin-events-workspace";

const api = vi.hoisted(() => ({ adminList: vi.fn(), create: vi.fn(), update: vi.fn(), publish: vi.fn(), cancel: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ communityEventsApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => ({ id: "admin-1", roles: ["SUPER_ADMIN"], permissions: [] }) }));

function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><AdminEventsWorkspace /></QueryClientProvider>);
}

describe("admin event workspace", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.adminList.mockResolvedValue({ data: { events: [] }, meta: { page: 1, pageSize: 20, total: 0 } });
    api.create.mockResolvedValue({ id: "event-1" });
  });

  it("creates a draft with tier, quota, dates, and capacity", async () => {
    const user = userEvent.setup();
    mount();

    await user.type(screen.getByLabelText("Tên sự kiện"), "Talk về di sản");
    await user.type(screen.getByLabelText("Mô tả"), "Gặp gỡ hội viên.");
    await user.type(screen.getByLabelText("Bắt đầu"), "2027-01-12T10:00");
    await user.type(screen.getByLabelText("Kết thúc"), "2027-01-12T11:00");
    await user.type(screen.getByLabelText(/Mở đăng ký chung/), "2027-01-10T10:00");
    await user.selectOptions(screen.getByLabelText(/Hạng được đăng ký ưu tiên/), "COMPANION");
    await user.type(screen.getByLabelText(/Mở đăng ký ưu tiên/), "2027-01-09T10:00");
    await user.type(screen.getByLabelText("Địa điểm"), "Hà Nội");
    await user.selectOptions(screen.getByLabelText("Hạng thẻ tối thiểu"), "SILVER");
    await user.selectOptions(screen.getByLabelText("Quyền lợi được dùng"), "TALK");
    await user.click(screen.getByRole("button", { name: "Tạo bản nháp" }));

    await waitFor(() => expect(api.create).toHaveBeenCalledWith(expect.objectContaining({
      title: "Talk về di sản", requiredTier: "SILVER", includedEntitlement: "TALK", entitlementQuota: 1,
      priorityTier: "COMPANION",
      capacity: 30, ticketPriceMinor: 0,
    })));
    const input = api.create.mock.calls[0]?.[0];
    expect(new Date(input.startsAt).toISOString()).toBe(input.startsAt);
    expect(new Date(input.priorityOpensAt).toISOString()).toBe(input.priorityOpensAt);
    expect(new Date(input.registrationOpensAt).toISOString()).toBe(input.registrationOpensAt);
  }, 15_000);
});
