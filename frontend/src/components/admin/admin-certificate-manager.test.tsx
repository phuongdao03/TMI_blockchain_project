import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminCertificateManager } from "@/components/admin/admin-certificate-manager";
import { adminCertificateApi } from "@/lib/api/client";
import type { AdminCertificate } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: {
    list: vi.fn(),
    contentDrafts: vi.fn().mockResolvedValue([]),
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
  it("links issued THV certificates to the dedicated correction page", async () => {
    vi.mocked(adminCertificateApi.list).mockResolvedValue({
      data: [
        {
          ...row,
          certificate: {
            ...row.certificate,
            certificateNumber: "THV-2026-0001",
            transactionHash: "0xconfirmed",
            blockchainStatus: "CONFIRMED",
          },
        },
      ],
      success: true,
      meta: { page: 1, pageSize: 10, total: 1 },
    });
    renderManager();
    expect(
      screen
        .getByRole("link", { name: "Sửa bằng đã cấp" })
        .getAttribute("href"),
    ).toBe("/admin/certificates/corrections");
    fireEvent.click(await screen.findByText("Quản lý hiển thị và phiên bản"));
    expect(
      screen
        .getByRole("link", { name: "Chỉnh nội dung bằng cũ" })
        .getAttribute("href"),
    ).toBe("/admin/certificates/corrections/certificate");
  });

  it("lets admin set listing preference without publishing the work", async () => {
    vi.mocked(adminCertificateApi.list).mockResolvedValue({
      data: [row],
      success: true,
      meta: { page: 1, pageSize: 20, total: 1 },
    });
    renderManager();
    fireEvent.click(await screen.findByText("Quản lý hiển thị và phiên bản"));
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

  it("filters and pages certificates while keeping direct verification", async () => {
    vi.mocked(adminCertificateApi.list).mockImplementation(async (filters) => ({
      data: [
        {
          ...row,
          certificate: {
            ...row.certificate,
            certificateNumber:
              filters?.page === 2 ? "CNS-2026-0002" : "CNS-2026-0001",
          },
        },
      ],
      success: true,
      meta: { page: filters?.page ?? 1, pageSize: 10, total: 11 },
    }));
    renderManager();

    fireEvent.change(screen.getByLabelText("Lọc trạng thái công bố"), {
      target: { value: "DRAFT" },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Trang sau" }));
    await waitFor(() =>
      expect(adminCertificateApi.list).toHaveBeenCalledWith({
        page: 2,
        pageSize: 10,
        search: undefined,
        status: undefined,
        publicationStatus: "DRAFT",
      }),
    );
    expect(
      await screen.findByRole("link", { name: /Xác minh CNS-2026-0002/ }),
    ).toBeTruthy();
    expect(screen.getByText("Chỉ tra cứu trực tiếp")).toBeTruthy();
  });
});
