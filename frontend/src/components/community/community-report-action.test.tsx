import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityReportAction } from "@/components/community/community-report-action";

const api = vi.hoisted(() => ({ reportPost: vi.fn(), reportComment: vi.fn() }));
const auth = vi.hoisted(() => ({
  user: { id: "member-1" } as { id: string } | null,
}));

vi.mock("@/lib/api/client", () => ({ communityReportApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => auth.user }));

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { mutations: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("CommunityReportAction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.user = { id: "member-1" };
    api.reportPost.mockResolvedValue({ id: "report-1", status: "OPEN" });
    api.reportComment.mockResolvedValue({ id: "report-2", status: "OPEN" });
  });

  it("submits a post report using one of the allowed reasons", async () => {
    const user = userEvent.setup();
    render(
      <CommunityReportAction
        targetId="post-1"
        targetLabel="Bài viết: Ký ức làng"
        targetType="POST"
      />,
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: "Báo cáo bài viết" }));
    await user.selectOptions(screen.getByLabelText("Lý do báo cáo"), "SPAM");
    await user.type(
      screen.getByLabelText("Chi tiết bổ sung (không bắt buộc)"),
      "Lặp lại quảng cáo.",
    );
    await user.click(screen.getByRole("button", { name: "Gửi báo cáo" }));

    expect(api.reportPost).toHaveBeenCalledWith("post-1", {
      reason: "SPAM",
      details: "Lặp lại quảng cáo.",
    });
    expect((await screen.findByRole("status")).textContent).toContain(
      "Đã gửi báo cáo",
    );
  });

  it("uses comment reporting and asks visitors to sign in", async () => {
    const user = userEvent.setup();
    render(
      <CommunityReportAction
        targetId="comment-1"
        targetLabel="Bình luận của Lan"
        targetType="COMMENT"
      />,
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: "Báo cáo bình luận" }));
    await user.selectOptions(
      screen.getByLabelText("Lý do báo cáo"),
      "HARASSMENT",
    );
    await user.click(screen.getByRole("button", { name: "Gửi báo cáo" }));
    expect(api.reportComment).toHaveBeenCalledWith("comment-1", {
      reason: "HARASSMENT",
    });

    auth.user = null;
    render(
      <CommunityReportAction
        targetId="post-2"
        targetLabel="Bài viết"
        targetType="POST"
      />,
      { wrapper },
    );
    expect(
      screen.getByRole("link", { name: "Đăng nhập để báo cáo" }),
    ).toBeDefined();
  });
});
