import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { CertificateContentCorrection } from "@/components/admin/certificate-content-correction";
import { adminCertificateApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  adminCertificateApi: {
    issuedContent: vi.fn(),
    requestContentCorrection: vi.fn(),
  },
}));

it("submits edited content for a new version while previewing removals", async () => {
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
    status: "PENDING_APPROVAL",
    changeReason: "Sửa nội dung tác giả trên bằng xác lập cũ.",
    requestedBy: "admin-1",
    requestedAt: "2026-10-06T00:00:00Z",
    decidedBy: null,
    decidedAt: null,
    rejectionReason: null,
    metadataHash: "a".repeat(64),
    blockchainTransactionId: null,
    pdfReady: false,
    createdAt: "2026-10-06T00:00:00Z",
  });
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <CertificateContentCorrection certificateId="certificate-1" />
    </QueryClientProvider>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Xóa tên người được ghi nhận" }),
  );
  expect(
    screen.getByLabelText("Xem trước nội dung phiên bản mới").textContent,
  ).not.toContain("Chưa công bố");
  fireEvent.change(screen.getByLabelText("Lý do chỉnh sửa"), {
    target: { value: "Sửa nội dung tác giả trên bằng xác lập cũ." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Gửi duyệt phiên bản mới" }));
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
          category: "Danh mục cũ",
        },
      },
    ),
  );
});
