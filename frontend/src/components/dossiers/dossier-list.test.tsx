import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DossierList } from "@/components/dossiers/dossier-list";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  dossierApi: { list: listMock },
}));

describe("DossierList", () => {
  it("renders filtered dossier records with status and next action", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
          code: "TMI-2026-ABCDEF123456",
          ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
          organizationId: null,
          categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
          title: "Bộ nhận diện TMI",
          slug: null,
          summary: "Hồ sơ quyền sở hữu.",
          status: "DRAFT",
          visibility: "PRIVATE",
          currentVersionNo: 0,
          submittedAt: null,
          createdAt: "2026-07-31T08:00:00Z",
          updatedAt: "2026-07-31T08:00:00Z",
          canEdit: true,
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 10, total: 1 },
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DossierList page={1} pageSize={10} status="DRAFT" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Bộ nhận diện TMI")).toBeDefined();
    expect(screen.getByText("Bản nháp")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Tiếp tục hoàn thiện" })
        .getAttribute("href"),
    ).toBe("/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac");
    expect(listMock).toHaveBeenCalledWith({
      page: 1,
      pageSize: 10,
      status: "DRAFT",
    });
  });
});
