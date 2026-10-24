import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
  myBenefitRequests: vi.fn(),
  submitBenefitRequest: vi.fn(),
  collaborationNeeds: vi.fn(),
}));
const communityApi = vi.hoisted(() => ({ directory: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  membershipApi: api,
  communityMemberApi: communityApi,
  ApiError: class extends Error {},
}));

import { MembershipBenefitCenter } from "./membership-benefit-center";

function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MembershipBenefitCenter tier="COMPANION" />
    </QueryClientProvider>,
  );
}

describe("membership benefit center", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.myBenefitRequests.mockResolvedValue({ requests: [] });
    api.collaborationNeeds.mockResolvedValue({
      requests: [
        {
          id: "need-1",
          displayName: "Nguyễn Minh",
          username: "minh-nguyen",
          statement: "Tìm đối tác phân phối sản phẩm thủ công.",
          createdAt: "2026-10-22T00:00:00Z",
        },
      ],
    });
    communityApi.directory.mockResolvedValue({ members: [], total: 0 });
  });

  it("submits a collaboration need and lists approved member needs", async () => {
    const user = userEvent.setup();
    api.submitBenefitRequest.mockResolvedValue({ id: "request-1" });
    mount();

    expect(
      await screen.findByText("Tìm đối tác phân phối sản phẩm thủ công."),
    ).toBeDefined();
    await user.type(
      screen.getByPlaceholderText(
        "Nêu mục tiêu, bối cảnh và thông tin cần thiết để xử lý yêu cầu.",
      ),
      "Tôi tìm cộng sự để phân phối sản phẩm thủ công.",
    );
    await user.click(screen.getByRole("button", { name: "Gửi yêu cầu" }));

    await waitFor(() =>
      expect(api.submitBenefitRequest).toHaveBeenCalledWith(
        "COLLABORATION_NEED",
        "Tôi tìm cộng sự để phân phối sản phẩm thủ công.",
      ),
    );
    expect(
      screen.getByText(
        "Nội dung sau khi được duyệt sẽ hiển thị với hội viên Vàng và Kim cương. Không nhập email, số điện thoại hoặc thông tin riêng tư.",
      ),
    ).toBeDefined();
  });

  it("searches public professional profiles for Gold members", async () => {
    const user = userEvent.setup();
    communityApi.directory.mockResolvedValue({
      total: 1,
      members: [
        {
          id: "member-1",
          username: "lan-design",
          displayName: "Lân Nguyễn",
          avatarUrl: null,
          membershipTier: "SILVER",
          professionalTitle: "Nhà thiết kế",
          organization: "Xưởng Việt",
          activityFields: "Thiết kế thủ công",
          professionalLinks: [],
        },
      ],
    });
    mount();

    await user.type(screen.getByLabelText("Từ khóa tìm hội viên"), "thiết kế");
    await user.click(screen.getByRole("button", { name: "Tìm hội viên" }));

    expect(await screen.findByText("Lân Nguyễn")).toBeDefined();
    expect(screen.getByText("Thiết kế thủ công")).toBeDefined();
    expect(
      screen.getByRole("link", { name: /Lân Nguyễn/ }).getAttribute("href"),
    ).toBe("/community/members/lan-design");
    expect(communityApi.directory).toHaveBeenCalledWith(
      "thiết kế",
      expect.anything(),
    );
  });
});
