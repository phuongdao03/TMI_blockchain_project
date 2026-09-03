import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ReviewQueuePage from "@/app/(dashboard)/reviews/page";

vi.mock("@/components/reviews/review-assignment-list", () => ({
  ReviewAssignmentList: () => <div>Danh sách phân công</div>,
}));

describe("ReviewQueuePage", () => {
  it("renders two balanced workflow steps and a compact filter group", async () => {
    const page = await ReviewQueuePage({ searchParams: Promise.resolve({}) });
    const { container } = render(page);

    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(
      container.querySelector(".review-queue__steps")?.className,
    ).toContain("sm:grid-cols-2");
    expect(
      container.querySelector(".review-queue__filters")?.className,
    ).toContain("sm:grid-cols-[minmax(16rem,28rem)_auto]");
  });
});
