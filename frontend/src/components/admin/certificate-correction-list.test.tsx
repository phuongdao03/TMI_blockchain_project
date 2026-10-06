import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { CertificateCorrectionList } from "@/components/admin/certificate-correction-list";
import { adminCertificateApi } from "@/lib/api/client";
import type { AdminCertificate } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: { list: vi.fn() },
}));

const certificate: AdminCertificate = {
  certificate: {
    id: "thv-id",
    certificateNumber: "THV-2026-001",
    dossierId: "dossier-id",
    dossierCode: "WORK-001",
    assetTitle: "Tác phẩm cũ",
    categoryName: "Nghệ thuật",
    currentVersionNo: 1,
    status: "ACTIVE",
    issuedAt: "2026-09-01T00:00:00Z",
    expiresAt: null,
    pdfReady: true,
    network: null,
    contractAddress: null,
    transactionHash: "0xconfirmed",
    blockchainStatus: "CONFIRMED",
    confirmations: 0,
  },
  publicWorkId: null,
  publicSlug: null,
  publicationStatus: null,
  visibility: null,
  isDiscoverable: false,
};

it("searches issued certificates and links active THV certificates to their editor", async () => {
  vi.mocked(adminCertificateApi.list).mockResolvedValue({
    data: [
      certificate,
      {
        ...certificate,
        certificate: {
          ...certificate.certificate,
          id: "legacy-id",
          certificateNumber: "CNS-2026-001",
        },
      },
      {
        ...certificate,
        certificate: {
          ...certificate.certificate,
          id: "unconfirmed-id",
          certificateNumber: "THV-2026-002",
          transactionHash: null,
          blockchainStatus: "BROADCAST",
        },
      },
    ],
    success: true,
    meta: { page: 1, pageSize: 10, total: 3 },
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <CertificateCorrectionList />
    </QueryClientProvider>,
  );

  fireEvent.change(screen.getByRole("searchbox", { name: "Tìm bằng đã cấp" }), {
    target: { value: "THV-2026" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Tìm kiếm" }));
  await waitFor(() =>
    expect(adminCertificateApi.list).toHaveBeenCalledWith({
      page: 1,
      pageSize: 10,
      search: "THV-2026",
      status: "ACTIVE",
    }),
  );
  expect(
    (
      await screen.findByRole("link", { name: "Sửa nội dung THV-2026-001" })
    ).getAttribute("href"),
  ).toBe("/admin/certificates/corrections/thv-id");
  expect(screen.queryByRole("link", { name: /Sửa nội dung CNS/ })).toBeNull();
  expect(
    screen.queryByRole("link", { name: /Sửa nội dung THV-2026-002/ }),
  ).toBeNull();
  expect(screen.getByText(/cần chuyển sang định dạng THV/)).toBeTruthy();
  expect(screen.getByText(/bản ghi blockchain đã xác nhận/)).toBeTruthy();
});
