import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { CertificateContentCorrection } from "@/components/admin/certificate-content-correction";
import { adminCertificateApi, publicWorkAdminApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: {
    issuedContent: vi.fn(),
    requestContentCorrection: vi.fn(),
  },
  publicWorkAdminApi: { categories: vi.fn() },
}));

it("submits edited content for a new version while previewing removals", async () => {
  vi.mocked(publicWorkAdminApi.categories).mockResolvedValue([
    {
      id: "category-1",
      parentId: null,
      code: "CERT",
      name: "Certificate",
      slug: "certificate",
      description: null,
      isActive: true,
      displayOrder: 0,
    },
    {
      id: "category-2",
      parentId: null,
      code: "OLD",
      name: "Danh mục ngừng sử dụng",
      slug: "old",
      description: null,
      isActive: false,
      displayOrder: 1,
    },
  ]);
  vi.mocked(adminCertificateApi.issuedContent).mockResolvedValue({
    certificateId: "certificate-1",
    certificateNumber: "THV-2026-TEST",
    currentVersionNo: 1,
    content: {
      title: "Tác phẩm cũ",
      summary: "Mô tả cũ",
      subject: "Chưa công bố",
      category: "Danh mục cũ",
    },
  });
  vi.mocked(adminCertificateApi.requestContentCorrection).mockResolvedValue({
    id: "version-2",
    certificateId: "certificate-1",
    versionNo: 2,
    dossierVersionId: "dossier-version-1",
    predecessorVersionId: "version-1",
    status: "ACTIVE",
    changeReason: "Sửa nội dung tác giả trên bằng xác lập cũ.",
    requestedBy: "admin-1",
    requestedAt: "2026-10-06T00:00:00Z",
    decidedBy: "admin-1",
    decidedAt: "2026-10-06T00:00:00Z",
    rejectionReason: null,
    metadataHash: "a".repeat(64),
    blockchainTransactionId: "proof-1",
    pdfReady: false,
    createdAt: "2026-10-06T00:00:00Z",
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <CertificateContentCorrection certificateId="certificate-1" />
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Xóa tên người được ghi nhận" }),
  );
  fireEvent.change(screen.getByLabelText("Lý do chỉnh sửa"), {
    target: { value: "Sửa nội dung tác giả trên bằng xác lập cũ." },
  });
  expect(screen.getByLabelText("Danh mục").tagName).toBe("SELECT");
  expect(
    screen.queryByRole("option", { name: "Danh mục ngừng sử dụng" }),
  ).toBeNull();
  expect(
    screen
      .getByRole("button", { name: "Lưu và phát hành bản điều chỉnh" })
      .hasAttribute("disabled"),
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Danh mục"), {
    target: { value: "Certificate" },
  });
  expect(
    screen.getByLabelText("Xem trước nội dung phiên bản mới").textContent,
  ).not.toContain("Chưa công bố");
  fireEvent.click(
    screen.getByRole("button", { name: "Lưu và phát hành bản điều chỉnh" }),
  );
  await waitFor(() =>
    expect(adminCertificateApi.requestContentCorrection).toHaveBeenCalledWith(
      "certificate-1",
      {
        expectedVersionNo: 1,
        reason: "Sửa nội dung tác giả trên bằng xác lập cũ.",
        content: {
          title: "Tác phẩm cũ",
          summary: "Mô tả cũ",
          subject: "",
          category: "Certificate",
        },
      },
    ),
  );
  expect(await screen.findByText(/Đã phát hành phiên bản mới/)).toBeDefined();
});
