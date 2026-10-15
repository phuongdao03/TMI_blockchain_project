import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { CommunityReportAction } from "@/components/community/community-report-action";

const api = vi.hoisted(() => ({ reportPost: vi.fn(), reportComment: vi.fn() }));
vi.mock("@/lib/api/client", () => ({ communityReportApi: api }));
vi.mock("@/lib/auth/user-context", () => ({ useAuthUser: () => ({ id: "member-1" }) }));

function wrapper({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={new QueryClient()}>{children}</QueryClientProvider>;
}

describe("community report reason options", () => {
  it("offers contract advertising and privacy violation reasons", async () => {
    const user = userEvent.setup();
    render(<CommunityReportAction targetId="post-1" targetLabel="post" targetType="POST" />, { wrapper });

    await user.click(screen.getByRole("button", { name: /báo cáo bài viết/i }));
    const values = screen.getAllByRole("option").map((option) => option.getAttribute("value"));

    expect(values).toContain("ADVERTISING");
    expect(values).toContain("PRIVACY_VIOLATION");
  });
});
