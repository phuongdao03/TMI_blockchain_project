import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MembershipWorkspace } from "./membership-workspace";

const api = vi.hoisted(() => ({
  chatAccess: vi.fn(),
  overview: vi.fn(),
  plans: vi.fn(),
  quote: vi.fn(),
  purchase: vi.fn(),
  myDiamondApplications: vi.fn(),
  submitDiamondApplication: vi.fn(),
  myBenefitRequests: vi.fn(),
  submitBenefitRequest: vi.fn(),
  collaborationNeeds: vi.fn(),
  messages: vi.fn(),
  send: vi.fn(),
  removeMessage: vi.fn(),
  summary: vi.fn(),
}));
const session = vi.hoisted(() => ({
  user: {
    id: "member-1",
    email: "member@example.vn",
    roles: ["USER"],
    permissions: [] as string[],
    accountType: "PUBLIC_USER",
  },
}));
vi.mock("@/lib/api/client", () => ({
  membershipApi: api,
  profileApi: { get: async () => ({ displayName: "Nguyễn Phương" }) },
  walletApi: { summary: api.summary },
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => session.user,
}));

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MembershipWorkspace />
    </QueryClientProvider>,
  );
}

describe("membership purchase", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    session.user = {
      id: "member-1",
      email: "member@example.vn",
      roles: ["USER"],
      permissions: [],
      accountType: "PUBLIC_USER",
    };
    api.chatAccess.mockResolvedValue({
      room: "MEMBER",
      allowed: true,
      source: "ADMIN",
    });
    api.overview.mockResolvedValue({
      tier: "MEMBER",
      memberNumber: "THV-MEMBER",
      status: "FREE",
      expiresAt: null,
      purchases: [],
      plans: [
        {
          id: "companion-plan",
          tier: "COMPANION",
          name: "Thẻ Đồng hành",
          amountMinor: 50_000,
          durationDays: 30,
          active: true,
        },
      ],
    });
    api.plans.mockResolvedValue({
      plans: [],
      member: {
        name: "Thành viên",
        description: "Hồ sơ cộng đồng cơ bản.",
        benefits: ["Tài khoản và hồ sơ cá nhân cơ bản."],
        conditions: "Được cấp miễn phí khi tạo tài khoản.",
      },
    });
    api.quote.mockResolvedValue({
      planId: "companion-plan",
      name: "Thẻ Đồng hành",
      tier: "COMPANION",
      kind: "NEW",
      fromTier: "MEMBER",
      listPriceMinor: 50_000,
      creditMinor: 0,
      amountDueMinor: 50_000,
      durationDays: 30,
      remainingDays: 0,
      expiresAt: "2027-01-01T00:00:00Z",
      approvalRequired: false,
    });
    api.myDiamondApplications.mockResolvedValue({ applications: [] });
    api.myBenefitRequests.mockResolvedValue({ requests: [] });
    api.collaborationNeeds.mockResolvedValue({ requests: [] });
    api.messages.mockResolvedValue({
      items: [],
      hasMore: false,
      nextCursor: null,
    });
  });

  const administratorCases: Array<[string, string[], string[]]> = [
    ["SUPER_ADMIN", ["SUPER_ADMIN"], []],
    ["membership manager", ["MODERATOR"], ["memberships.manage"]],
  ];

  it.each(administratorCases)(
    "hides personal membership actions from %s and keeps room access",
    async (_label, roles, permissions) => {
      session.user = {
        id: "admin-1",
        email: "admin@example.vn",
        roles,
        permissions,
        accountType: "PUBLIC_USER",
      };
      api.chatAccess.mockResolvedValue({
        room: "MEMBER",
        allowed: true,
        source: "ADMIN",
      });
      mount();

      expect(
        await screen.findByRole("heading", { name: "Không gian hội viên" }),
      ).toBeDefined();
      expect(
        await screen.findByText("Quyền quản trị · mọi phòng"),
      ).toBeDefined();
      expect(
        screen.queryByRole("button", {
          name: /Đăng ký bằng ví|Gia hạn bằng ví/,
        }),
      ).toBeNull();
      expect(
        screen.queryByRole("button", { name: "Gửi yêu cầu xét duyệt" }),
      ).toBeNull();
      expect(api.overview).not.toHaveBeenCalled();
      expect(api.plans).not.toHaveBeenCalled();
      expect(api.myDiamondApplications).not.toHaveBeenCalled();
    },
  );

  it("keeps the purchase idempotency key after an uncertain result and dialog reopen", async () => {
    const user = userEvent.setup();
    api.summary.mockResolvedValue({ balanceMinor: 100_000 });
    api.purchase.mockRejectedValue(new Error("response lost"));
    mount();
    await user.click(
      await screen.findByRole("button", { name: "Đăng ký bằng ví" }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Thanh toán bằng ví" }),
    );
    await screen.findByText(
      "Chưa thể đăng ký thẻ. Vui lòng kiểm tra lại giao dịch.",
    );
    await user.click(screen.getByRole("button", { name: "Quay lại" }));
    await user.click(screen.getByRole("button", { name: "Đăng ký bằng ví" }));
    await user.click(
      screen.getByRole("button", { name: "Thanh toán bằng ví" }),
    );
    await waitFor(() => expect(api.purchase).toHaveBeenCalledTimes(2));
    expect(api.purchase.mock.calls[0]).toEqual(api.purchase.mock.calls[1]);
    expect(api.purchase.mock.calls[0]?.[0]).toBe("companion-plan");
    expect(api.purchase.mock.calls[0]?.[2]).toEqual({
      expectedAmountMinor: 50_000,
      renewalOptIn: false,
    });
  });

  it("shows the shortfall and blocks confirmation when the wallet is insufficient", async () => {
    const user = userEvent.setup();
    api.summary.mockResolvedValue({ balanceMinor: 10_000 });
    mount();
    await user.click(
      await screen.findByRole("button", { name: "Đăng ký bằng ví" }),
    );
    await screen.findByRole("link", { name: "Nạp tiền vào ví" });
    expect(
      screen.getByRole("button", { name: "Thanh toán bằng ví" }),
    ).toHaveProperty("disabled", true);
    expect(api.purchase).not.toHaveBeenCalled();
  });

  it("requires Diamond approval before allowing payment", async () => {
    const user = userEvent.setup();
    api.overview.mockResolvedValue({
      tier: "MEMBER",
      memberNumber: "THV-MEMBER",
      status: "FREE",
      expiresAt: null,
      purchases: [],
      plans: [
        {
          id: "diamond-plan",
          tier: "PRESTIGE",
          name: "Tinh hoa",
          amountMinor: 3_990_000,
          durationDays: 365,
          active: true,
        },
      ],
    });
    api.quote.mockResolvedValue({
      planId: "diamond-plan",
      name: "Tinh hoa",
      tier: "PRESTIGE",
      kind: "NEW",
      fromTier: "MEMBER",
      listPriceMinor: 3_990_000,
      creditMinor: 0,
      amountDueMinor: 3_990_000,
      durationDays: 365,
      remainingDays: 0,
      expiresAt: "2027-10-22T00:00:00Z",
      approvalRequired: true,
    });
    api.summary.mockResolvedValue({ balanceMinor: 9_000_000 });
    api.submitDiamondApplication.mockResolvedValue({ status: "PENDING" });
    mount();

    await user.click(
      await screen.findByRole("button", { name: "Đăng ký bằng ví" }),
    );
    await screen.findByText(/cần được xét duyệt/);
    expect(
      screen.getByRole("button", { name: "Thanh toán bằng ví" }),
    ).toHaveProperty("disabled", true);
    expect(api.purchase).not.toHaveBeenCalled();
    await user.type(
      screen.getByLabelText("Giới thiệu lý do đăng ký Kim cương"),
      "Tôi muốn tham gia cộng đồng chuyên sâu.",
    );
    await user.click(
      screen.getByRole("button", { name: "Gửi yêu cầu xét duyệt" }),
    );
    await waitFor(() =>
      expect(api.submitDiamondApplication).toHaveBeenCalledWith(
        "Tôi muốn tham gia cộng đồng chuyên sâu.",
      ),
    );
  });
});
