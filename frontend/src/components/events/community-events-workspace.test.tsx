import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityEventsWorkspace } from "./community-events-workspace";

const api = vi.hoisted(() => ({
  list: vi.fn(), myRegistrations: vi.fn(), register: vi.fn(), cancelRegistration: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({ communityEventsApi: api, ApiError: class extends Error { status = 403; } }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => ({ id: "member-1" }) }));

function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><CommunityEventsWorkspace /></QueryClientProvider>);
}

const event = {
  id: "event-1", title: "Talk về di sản", description: "Gặp gỡ hội viên.",
  startsAt: "2027-01-12T10:00:00Z", endsAt: "2027-01-12T11:00:00Z",
  registrationOpensAt: "2027-01-11T10:00:00Z", priorityTier: "COMPANION" as const,
  priorityOpensAt: "2027-01-10T10:00:00Z",
  location: "Hà Nội", requiredTier: "SILVER" as const, capacity: 10,
  confirmedCount: 2, ticketPriceMinor: 0, cancellationCutoffAt: null,
  includedEntitlement: "TALK" as const, entitlementQuota: 1,
  requiresDiamondApproval: false, status: "PUBLISHED" as const,
  createdByUserId: "admin-1", createdAt: "2026-10-01T00:00:00Z",
  updatedAt: "2026-10-01T00:00:00Z",
};

describe("community events", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.list.mockResolvedValue({ data: { events: [event] }, meta: { page: 1, pageSize: 20, total: 1 } });
    api.myRegistrations.mockResolvedValue({ registrations: [] });
  });

  it("shows eligibility and submits registration through the event API", async () => {
    const user = userEvent.setup();
    api.register.mockResolvedValue({ eventId: event.id, status: "CONFIRMED" });
    mount();

    expect(await screen.findByText("Talk về di sản")).toBeDefined();
    expect(screen.getByText("Dùng 1 lượt Talk")).toBeDefined();
    expect(screen.getByText(/Hội viên Vàng trở lên được đăng ký ưu tiên/)).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Đăng ký tham gia" }));
    await waitFor(() => expect(api.register.mock.calls[0]?.[0]).toBe(event.id));
  });

  it("does not imply paid tickets are registered", async () => {
    api.list.mockResolvedValue({ data: { events: [{ ...event, ticketPriceMinor: 250_000, includedEntitlement: null, entitlementQuota: null }] }, meta: { page: 1, pageSize: 20, total: 1 } });
    mount();

    expect((await screen.findByRole("button", { name: "Cần thanh toán vé" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Thanh toán vé trực tuyến chưa được kết nối.")).toBeDefined();
    expect(api.register).not.toHaveBeenCalled();
  });

  it("shows prior registrations outside the public event listing", async () => {
    api.list.mockResolvedValue({ data: { events: [] }, meta: { page: 1, pageSize: 20, total: 0 } });
    api.myRegistrations.mockResolvedValue({ registrations: [{
      registration: { id: "registration-1", status: "CANCELLED" }, event,
    }] });
    mount();

    expect(await screen.findByText("Talk về di sản")).toBeDefined();
    expect(screen.getByText("Đã hủy")).toBeDefined();
    expect(screen.getByRole("heading", { name: "Đăng ký của tôi" })).toBeDefined();
  });

  it("keeps the newest registration state when an event has re-registration history", async () => {
    api.myRegistrations.mockResolvedValue({ registrations: [
      { registration: { id: "new-registration", status: "CONFIRMED" }, event },
      { registration: { id: "old-registration", status: "CANCELLED" }, event },
    ] });
    mount();

    expect(await screen.findByRole("button", { name: "Hủy đăng ký" })).toBeDefined();
  });

  it("pages through a long public event listing", async () => {
    const user = userEvent.setup();
    api.list.mockResolvedValue({ data: { events: [] }, meta: { page: 1, pageSize: 20, total: 21 } });
    mount();

    await user.click(await screen.findByRole("button", { name: "Sau" }));
    await waitFor(() => expect(api.list).toHaveBeenCalledWith(2));
  });
});
