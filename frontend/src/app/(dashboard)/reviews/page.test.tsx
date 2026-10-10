import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import ReviewQueuePage from "@/app/(dashboard)/reviews/page";

vi.mock("@/components/reviews/review-assignment-list", () => ({
  ReviewAssignmentList: () => <div>Danh sách phân công</div>,
}));

describe("ReviewQueuePage", () => {
  it("renders a focused reviewer header and compact filter group", async () => {
    const user = userEvent.setup();
    const page = await ReviewQueuePage({ searchParams: Promise.resolve({}) });
    const { container } = render(page);

    expect(
      screen.getByRole("heading", { name: "Công việc kiểm duyệt" }),
    ).toBeDefined();
    expect(screen.queryByRole("listitem")).toBeNull();
    const filters = container.querySelector<HTMLDetailsElement>(
      ".review-queue__filters",
    );
    expect(filters?.open).toBe(false);
    await user.click(screen.getByText("Bộ lọc · Tất cả phân công"));
    expect(filters?.open).toBe(true);
    expect(
      screen.getByRole("button", { name: "Áp dụng bộ lọc" }),
    ).toBeDefined();
  });
});
