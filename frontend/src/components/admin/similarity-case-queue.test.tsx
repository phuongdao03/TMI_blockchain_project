import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SimilarityCaseQueue } from "@/components/admin/similarity-case-queue";

const listAdmin = vi.hoisted(() => vi.fn());
const assign = vi.hoisted(() => vi.fn());
const listStaff = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  similarityApi: { listAdmin, assign },
  staffAccountsApi: { list: listStaff },
}));

describe("SimilarityCaseQueue", () => {
  it("lets an administrator assign an open comparison without exposing policy codes", async () => {
    listAdmin.mockResolvedValue({
      data: [
        {
          id: "case-1",
          status: "OPEN",
          signalType: "IMAGE",
          leftAsset: {
            dossierCode: "HS-001",
            dossierTitle: "Sắc thu",
            versionNo: 1,
            evidenceMediaIds: [],
          },
          rightAsset: {
            dossierCode: "HS-002",
            dossierTitle: "Mùa thu",
            versionNo: 1,
            evidenceMediaIds: [],
          },
          policyVersion: "near-duplicate-v1",
          imageDistance: 3,
          textScore: null,
        },
      ],
      meta: { total: 1 },
    });
    listStaff.mockResolvedValue({
      data: [
        {
          id: "reviewer-1",
          email: "reviewer@tmi.vn",
          role: "MODERATOR",
          status: "ACTIVE",
        },
      ],
      meta: { total: 1 },
    });
    assign.mockResolvedValue({ id: "case-1", status: "ASSIGNED" });
    const user = userEvent.setup();

    render(
      <QueryClientProvider client={new QueryClient()}>
        <SimilarityCaseQueue />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Sắc thu")).toBeDefined();
    expect(screen.queryByText("near-duplicate-v1")).toBeNull();
    await screen.findByRole("option", { name: "reviewer@tmi.vn" });
    await user.selectOptions(
      screen.getByLabelText("Chuyên gia phụ trách"),
      "reviewer-1",
    );
    await user.click(screen.getByRole("button", { name: "Giao xử lý" }));
    expect(assign).toHaveBeenCalledWith("case-1", "reviewer-1");
  });
});
