import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CertificateDetail } from "@/components/certificates/certificate-detail";

const getMock = vi.hoisted(() => vi.fn());
const versionsMock = vi.hoisted(() => vi.fn());
const dossierVersionsMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  certificateApi: {
    get: getMock,
    versions: versionsMock,
    download: vi.fn(),
    requestVersion: vi.fn(),
  },
  dossierApi: { versions: dossierVersionsMock },
}));

describe("CertificateDetail", () => {
  it("explains version history with user language", async () => {
    getMock.mockResolvedValue({
      certificate: {
        id: "certificate-1",
        dossierId: "dossier-1",
        certificateNumber: "TMI-2026-0001",
        assetTitle: "Bộ nhận diện TMI",
        currentVersionNo: 2,
        status: "ACTIVE",
        pdfReady: true,
        network: "polygon",
        transactionHash: "0x1234",
        confirmations: 64,
      },
      metadataHash: "a".repeat(64),
      qrPayload: "/verify/TMI-2026-0001",
    });
    versionsMock.mockResolvedValue([
      {
        id: "version-2",
        certificateId: "certificate-1",
        versionNo: 2,
        dossierVersionId: "dossier-version-2",
        predecessorVersionId: "version-1",
        status: "ACTIVE",
        changeReason: "Cập nhật thông tin chủ thể theo hồ sơ đã duyệt.",
        requestedAt: "2026-08-11T09:00:00Z",
        createdAt: "2026-08-11T09:00:00Z",
      },
      {
        id: "version-1",
        certificateId: "certificate-1",
        versionNo: 1,
        dossierVersionId: "dossier-version-1",
        predecessorVersionId: null,
        status: "SUPERSEDED",
        changeReason: null,
        requestedAt: null,
        createdAt: "2026-08-01T09:00:00Z",
      },
    ]);
    dossierVersionsMock.mockResolvedValue([
      { id: "dossier-version-2", versionNo: 2 },
      { id: "dossier-version-1", versionNo: 1 },
    ]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={client}>
        <CertificateDetail id="certificate-1" />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Bộ nhận diện TMI")).toBeDefined();
    expect(screen.getAllByText("Đang có hiệu lực").length).toBeGreaterThan(0);
    expect(screen.getByText("Đã được cập nhật")).toBeDefined();
    expect(screen.getByText("Chưa có thay đổi cần cập nhật")).toBeDefined();
    expect(screen.queryByText("ACTIVE")).toBeNull();
    expect(
      screen.queryByText(/SUPER_ADMIN|database|schema|endpoint/i),
    ).toBeNull();
  });
});
