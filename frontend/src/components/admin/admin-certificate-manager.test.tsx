import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminCertificateManager } from "@/components/admin/admin-certificate-manager";
import { adminCertificateApi } from "@/lib/api/client";
import type { AdminCertificate } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: {
    list: vi.fn(),
    configureListing: vi
      .fn()
      .mockResolvedValue({ showCertificate: true, publicWorkVersion: 3 }),
  },
}));
const row: AdminCertificate = {
  certificate: {
    id: "certificate",
    certificateNumber: "CNS-2026-0001",
    status: "ACTIVE",
    assetTitle: "Tác phẩm",
    dossierCode: "WORK-001",
    currentVersionNo: 1,
    dossierId: "dossier",
    categoryName: "Nghệ thuật",
    issuedAt: "2026-09-01T00:00:00Z",
    expiresAt: null,
    pdfReady: false,
    network: null,
    contractAddress: null,
    transactionHash: null,
    blockchainStatus: null,
    confirmations: 0,
  },
  publicWorkId: "work",
  publicationStatus: "DRAFT",
  publicWorkVersion: 2,
  showCertificate: false,
  isDiscoverable: false,
  publicSlug: "work",
  visibility: "PUBLIC",
};

function renderManager() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AdminCertificateManager />
    </QueryClientProvider>,
  );
}

describe("AdminCertificateManager", () => {
  it("lets admin set listing preference without publishing the work", async () => {
    vi.mocked(adminCertificateApi.list).mockResolvedValue({
      data: [row],
      success: true,
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    renderManager();
    fireEvent.click(
      await screen.findByRole("button", { name: "Cho hiển thị cùng tác phẩm" }),
    );
    await waitFor(() =>
      expect(adminCertificateApi.configureListing).toHaveBeenCalledWith(
        "certificate",
        { expectedWorkVersion: 2, showCertificate: true },
      ),
    );
    expect(screen.getByText(/chưa công bố/)).toBeTruthy();
    expect(
      screen
        .getByRole("link", { name: "Tạo phiên bản điều chỉnh" })
        .getAttribute("href"),
    ).toBe("/certificates/certificate#certificate-update");
  });
  it("does not offer listing for revoked certificates", async () => {
    vi.mocked(adminCertificateApi.list).mockResolvedValue({
      data: [
        { ...row, certificate: { ...row.certificate, status: "REVOKED" } },
      ],
      success: true,
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    renderManager();
    expect(await screen.findByText("Đã thu hồi · chỉ tra cứu")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Cho hiển thị cùng tác phẩm" }),
    ).toBeNull();
  });
});
