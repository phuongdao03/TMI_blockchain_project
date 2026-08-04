import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CertificateList } from "@/components/certificates/certificate-list";

const listMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  certificateApi: { list: listMock },
}));

describe("CertificateList", () => {
  it("shows issued certificate and opens its proof detail", async () => {
    listMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "7eaec2d2-c99a-42c9-8f1e-71462ba01ea0",
          certificateNumber: "TMI-2026-7EAEC2D2C99A",
          dossierId: "dossier-id",
          dossierCode: "DOS-1",
          assetTitle: "Bộ nhận diện TMI",
          categoryName: "Thương hiệu",
          currentVersionNo: 1,
          status: "ACTIVE",
          issuedAt: "2026-07-31T00:00:00Z",
          expiresAt: null,
          pdfReady: true,
          network: "local",
          contractAddress: "0x12",
          transactionHash: "0x34",
          blockchainStatus: "CONFIRMED",
          confirmations: 1,
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 12, total: 1 },
    });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <CertificateList page={1} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Bộ nhận diện TMI")).toBeDefined();
    expect(
      screen.getByRole("link", { name: /Xem chứng thư/ }).getAttribute("href"),
    ).toBe("/chung-thu/7eaec2d2-c99a-42c9-8f1e-71462ba01ea0");
  });
});
