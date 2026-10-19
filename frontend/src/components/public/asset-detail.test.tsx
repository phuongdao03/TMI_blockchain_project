import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssetDetail } from "@/components/public/asset-detail";

const asset = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({ publicApi: { asset } }));

describe("AssetDetail", () => {
  it("shows the public verification path without internal details", async () => {
    asset.mockResolvedValue({
      asset: {
        slug: "tac-pham",
        title: "Tác phẩm Tinh Hoa Việt",
        summary: "Hồ sơ đã công bố",
        categoryCode: "ART",
        categoryName: "Mỹ thuật",
        certificateNumber: "THV-2026-001",
        certificateStatus: "ACTIVE",
        issuedAt: "2026-09-01T00:00:00Z",
        transactionHash: "0xabcd",
      },
      metadata: { creator: "Nghệ nhân Việt" },
      network: "polygon-mainnet",
      contractAddress: "0x4B7fFF9e719a55cA3792cF96fbb229611e505b5F",
      confirmations: 18,
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <AssetDetail slug="tac-pham" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Kiểm tra bằng xác lập")).toBeDefined();
    expect(screen.getAllByText("THV-2026-001")).toHaveLength(2);
    expect(
      screen
        .getByRole("link", { name: /Tra cứu bằng xác lập/ })
        .getAttribute("href"),
    ).toBe("/verify/THV-2026-001");
    expect(screen.queryByText(/blockchain|polygon|0xabcd|0x4B7f/i)).toBeNull();
  });
});
