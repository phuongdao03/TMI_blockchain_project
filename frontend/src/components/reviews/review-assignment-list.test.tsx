import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ReviewAssignmentList } from "@/components/reviews/review-assignment-list";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  reviewApi: { list: listMock },
}));

describe("ReviewAssignmentList", () => {
  it("renders the reviewer queue and assignment action", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          assignment: {
            id: "4155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dossierVersionId: "8155dbf5-bb3e-449d-8bf0-9572cc642cac",
            reviewerUserId: "7155dbf5-bb3e-449d-8bf0-9572cc642cac",
            assignedBy: "6155dbf5-bb3e-449d-8bf0-9572cc642cac",
            dueAt: "2026-08-08T08:00:00Z",
            status: "ASSIGNED",
            conflictDeclaredAt: null,
            conflictReason: null,
          },
          dossierCode: "HS-2026-000001",
          dossierTitle: "Hồ sơ thương hiệu TMI",
          versionNo: 1,
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 10, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <ReviewAssignmentList page={1} pageSize={10} status="ASSIGNED" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Hồ sơ thương hiệu TMI")).toBeDefined();
    expect(screen.getByText("Chờ xác nhận")).toBeDefined();
    expect(
      screen.getByText("Bước tiếp theo: Xác nhận xung đột lợi ích"),
    ).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Mở hồ sơ thẩm định" })
        .getAttribute("href"),
    ).toBe("/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac");
  });
});
