import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MembershipAdminWorkspace } from "./membership-admin-workspace";

const api = vi.hoisted(() => ({
  plans: vi.fn(),
  overview: vi.fn(),
  publishPlan: vi.fn(),
  retirePlan: vi.fn(),
  diamondApplications: vi.fn(),
  reviewDiamondApplication: vi.fn(),
  benefitRequests: vi.fn(),
  reviewBenefitRequest: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  membershipApi: api,
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ roles: ["SUPER_ADMIN"], permissions: [] }),
}));

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MembershipAdminWorkspace />
    </QueryClientProvider>,
  );
}

describe("membership administration", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.plans.mockResolvedValue({
      plans: [],
      member: {
        name: "Member",
        description: "Basic tier",
        benefits: [],
        conditions: "",
      },
    });
    api.diamondApplications.mockResolvedValue({
      applications: [
        {
          id: "application-1",
          userId: "user-1",
          statement: "Tôi muốn tham gia hoạt động chuyên sâu.",
          status: "PENDING",
          decisionNote: null,
          createdAt: "2026-10-22T00:00:00Z",
        },
      ],
    });
    api.benefitRequests.mockResolvedValue({ requests: [] });
  });

  it("loads the plan catalog without loading a personal membership", async () => {
    api.plans.mockResolvedValue({
      plans: [
        {
          id: "silver-plan",
          name: "Existing Silver",
          tier: "SILVER",
          amountMinor: 490_000,
          durationDays: 365,
          description: "Membership package",
          benefits: ["Community talks"],
          conditions: "",
          active: true,
        },
      ],
      member: {
        name: "Member",
        description: "Basic tier",
        benefits: [],
        conditions: "",
      },
    });

    mount();

    expect(await screen.findByText("Existing Silver")).toBeDefined();
    expect(api.plans).toHaveBeenCalledOnce();
    expect(api.overview).not.toHaveBeenCalled();
  });

  it("allows admins to configure a Silver plan from backend-owned copy", async () => {
    const user = userEvent.setup();
    api.publishPlan.mockResolvedValue({ id: "silver-plan" });
    mount();

    await user.type(screen.getByLabelText("Tên gói"), "Kết nối Bạc");
    await user.clear(screen.getByLabelText("Giá gói (VNĐ)"));
    await user.type(screen.getByLabelText("Giá gói (VNĐ)"), "490000");
    await user.clear(screen.getByLabelText("Thời hạn (ngày)"));
    await user.type(screen.getByLabelText("Thời hạn (ngày)"), "365");
    await user.type(screen.getByLabelText("Mô tả"), "Mở rộng kết nối.");
    await user.type(
      screen.getByLabelText("Quyền lợi bổ sung (mỗi dòng một quyền lợi)"),
      "4 buổi Talk mỗi năm",
    );
    await user.click(screen.getByRole("button", { name: "Mở đăng ký gói" }));

    await waitFor(() =>
      expect(api.publishPlan).toHaveBeenCalledWith({
        name: "Kết nối Bạc",
        tier: "SILVER",
        amountMinor: 490_000,
        durationDays: 365,
        description: "Mở rộng kết nối.",
        benefits: ["4 buổi Talk mỗi năm"],
        conditions: "",
      }),
    );
  });

  it("records an explicit Diamond application decision and note", async () => {
    const user = userEvent.setup();
    api.reviewDiamondApplication.mockResolvedValue({ status: "APPROVED" });
    mount();

    await user.type(
      screen.getByLabelText("Ghi chú quyết định"),
      "Đủ điều kiện.",
    );
    await user.click(screen.getByRole("button", { name: "Duyệt" }));

    await waitFor(() =>
      expect(api.reviewDiamondApplication).toHaveBeenCalledWith(
        "application-1",
        "approve",
        "Đủ điều kiện.",
      ),
    );
  });

  it("sends a benefit request decision with the admin note", async () => {
    const user = userEvent.setup();
    api.benefitRequests.mockResolvedValue({
      requests: [
        {
          id: "benefit-1",
          userId: "member-1",
          benefit: "ADVISORY_SESSION",
          cycleStartedAt: "2026-10-22T00:00:00Z",
          statement: "Tôi cần tư vấn phát triển sản phẩm.",
          status: "PENDING",
          decisionNote: null,
          reviewedByUserId: null,
          reviewedAt: null,
          createdAt: "2026-10-22T00:00:00Z",
          updatedAt: "2026-10-22T00:00:00Z",
        },
      ],
    });
    api.reviewBenefitRequest.mockResolvedValue({ status: "APPROVED" });
    mount();

    await user.type(
      screen.getByLabelText("Ghi chú xử lý"),
      "Đã tiếp nhận, điều phối lịch sau.",
    );
    await user.click(screen.getByRole("button", { name: "Tiếp nhận" }));

    await waitFor(() =>
      expect(api.reviewBenefitRequest).toHaveBeenCalledWith(
        "benefit-1",
        "approve",
        "Đã tiếp nhận, điều phối lịch sau.",
      ),
    );
  });
});
