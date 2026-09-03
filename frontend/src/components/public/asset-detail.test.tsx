import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssetDetail } from "@/components/public/asset-detail";

const asset = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({ publicApi: { asset } }));

describe("AssetDetail", () => {
  it("presents blockchain evidence in plain Vietnamese and keeps technical data advanced", async () => {
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

    expect(await screen.findByText("Xác minh blockchain")).toBeDefined();
    expect(
      screen.getByText(
        "Bản ghi blockchain đã được công bố. Hãy tra cứu chứng thư để kiểm tra trạng thái mới nhất.",
      ),
    ).toBeDefined();
    expect(screen.getByText("Mã giao dịch trên blockchain")).toBeDefined();
    expect(screen.getByText("Số lượt mạng đã xác nhận")).toBeDefined();
    expect(screen.getByText("Địa chỉ sổ đăng ký công khai")).toBeDefined();
    expect(screen.getByText("Blockchain là gì?")).toBeDefined();
    expect(screen.getByText("Chi tiết nâng cao")).toBeDefined();
  });
});
