import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ plans: vi.fn() }));

vi.mock("@/lib/api/client", () => ({ membershipApi: api }));

import { MembershipPricingPage } from "./membership-pricing-page";

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MembershipPricingPage />
    </QueryClientProvider>,
  );
}

describe("public membership pricing page", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.plans.mockResolvedValue({
      plans: [
        {
          id: "silver",
          tier: "SILVER",
          name: "Kết nối",
          amountMinor: 490_000,
          durationDays: 365,
          description: "Mở rộng tri thức và kết nối.",
          benefits: ["4 chương trình Tinh Hoa Talk chuyên đề mỗi năm."],
          conditions: "Áp dụng theo điều kiện chương trình.",
          active: true,
        },
        {
          id: "gold",
          tier: "COMPANION",
          name: "Đồng hành",
          amountMinor: 1_490_000,
          durationDays: 365,
          description: "Cùng vun bồi giá trị Việt.",
          benefits: ["Phòng chat Đồng hành."],
          conditions: "Không bảo đảm kết quả hợp tác.",
          active: true,
        },
        {
          id: "diamond",
          tier: "PRESTIGE",
          name: "Tinh hoa",
          amountMinor: 3_990_000,
          durationDays: 365,
          description: "Kết nối chuyên sâu.",
          benefits: ["Tối đa 2 buổi Circle mỗi năm."],
          conditions: "Phải được xét duyệt trước khi thanh toán.",
          active: true,
        },
      ],
      member: {
        name: "Thành viên",
        description: "Bắt đầu kết nối.",
        benefits: ["Tài khoản và hồ sơ cá nhân cơ bản."],
        conditions: "Được cấp miễn phí khi tạo tài khoản.",
      },
    });
  });

  it("shows the four approved tiers with catalog prices, marketing assets, and Diamond approval terms", async () => {
    mount();

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "HỘI VIÊN TINH HOA VIỆT",
      }),
    ).toBeDefined();
    expect(
      screen.getByText(
        "Kết nối giá trị – Đồng hành phát triển – Lan tỏa tinh hoa.",
      ),
    ).toBeDefined();
    await screen.findByRole("article", { name: /Bạc.*Kết nối/i });

    const expectedPlans = [
      ["Đồng", "Thành viên", "Miễn phí"],
      ["Bạc", "Kết nối", "490.000"],
      ["Vàng", "Đồng hành", "1.490.000"],
      ["Kim cương", "Tinh hoa", "3.990.000"],
    ] as const;
    for (const [tier, planName, price] of expectedPlans) {
      const card = screen.getByRole("article", {
        name: new RegExp(`${tier}.*${planName}`, "i"),
      });
      expect(card.textContent).toContain(price);
      expect(within(card).getByRole("link").getAttribute("href")).toBe(
        tier === "Đồng" ? "/register?next=%2Fmembership" : "/membership",
      );
    }

    expect(
      screen.getByRole("img", { name: "Huy hiệu cấp Đồng" }),
    ).toBeDefined();
    expect(screen.getByRole("img", { name: "Huy hiệu cấp Bạc" })).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Huy hiệu cấp Vàng" }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Huy hiệu cấp Kim cương" }),
    ).toBeDefined();
    expect(screen.getByText("Được đề xuất")).toBeDefined();
    expect(
      screen.getByText(/phải được xét duyệt trước khi thanh toán/i),
    ).toBeDefined();
    expect(
      screen.getAllByText(/không đồng nghĩa với chứng nhận Tinh Hoa Việt/i)
        .length,
    ).toBeGreaterThan(0);

    const freeTierBenefit = screen.getByRole("row", {
      name: /Tài khoản và hồ sơ cá nhân cơ bản/i,
    });
    expect(
      within(freeTierBenefit)
        .getAllByRole("img")
        .map((status) => status.getAttribute("aria-label")),
    ).toEqual(Array(4).fill("Có quyền lợi"));

    const diamondBenefit = screen.getByRole("row", {
      name: /Tối đa 2 buổi Circle mỗi năm/i,
    });
    expect(
      within(diamondBenefit)
        .getAllByRole("img")
        .map((status) => status.getAttribute("aria-label")),
    ).toEqual([
      "Chưa có quyền lợi",
      "Chưa có quyền lợi",
      "Chưa có quyền lợi",
      "Có quyền lợi",
    ]);
    expect(screen.queryByText("Bao gồm", { exact: true })).toBeNull();
    expect(
      screen.getAllByText(/xem đủ \d+ quyền lợi và điều kiện/i).length,
    ).toBe(4);
  });

  it("explains when the catalog is unavailable instead of implying paid plans are closed", async () => {
    api.plans.mockRejectedValueOnce(new Error("catalog unavailable"));
    mount();

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Bảng giá hội viên hiện chưa kết nối được",
    );
    expect(
      screen.getByText(/chưa có dữ liệu quyền lợi để hiển thị bảng so sánh/i),
    ).toBeDefined();
    expect(screen.queryByText("Chưa mở đăng ký")).toBeNull();
  });
});
