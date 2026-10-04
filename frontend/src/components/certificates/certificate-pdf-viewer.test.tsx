import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { CertificatePdfViewer } from "@/components/certificates/certificate-pdf-viewer";

const downloadPdf = vi.hoisted(() => vi.fn());
const getDocument = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  certificateApi: { downloadPdf },
}));

vi.mock("pdfjs-dist", () => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument,
}));

beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("offers the original PDF when the canvas renderer cannot read an older file", async () => {
  downloadPdf.mockResolvedValue(
    new Blob(["%PDF-1.4"], { type: "application/pdf" }),
  );
  getDocument.mockImplementation(() => ({
    promise: Promise.reject(new Error("Unsupported PDF")),
    destroy: vi.fn(),
  }));

  render(
    <CertificatePdfViewer
      certificateId="legacy-certificate"
      certificateNumber="CNS-2026-OLD"
      onDownload={vi.fn()}
    />,
  );

  const link = await screen.findByRole("link", {
    name: "Mở bằng xác lập PDF",
  });
  expect(link.getAttribute("href")).toBe(
    "/api/v1/certificates/legacy-certificate/pdf?inline=1",
  );
  expect(
    (
      screen.getByRole("button", {
        name: "Mở PDF trong thẻ mới",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("offers a retry when the PDF could not be fetched", async () => {
  downloadPdf.mockRejectedValueOnce(new Error("Unavailable"));
  downloadPdf.mockResolvedValueOnce(
    new Blob(["%PDF-1.4"], { type: "application/pdf" }),
  );
  getDocument.mockImplementation(() => ({
    promise: Promise.reject(new Error("Unsupported PDF")),
    destroy: vi.fn(),
  }));

  render(
    <CertificatePdfViewer
      certificateId="legacy-certificate"
      certificateNumber="CNS-2026-OLD"
      onDownload={vi.fn()}
    />,
  );

  (await screen.findByRole("button", { name: "Tải lại PDF" })).click();
  await waitFor(() => expect(downloadPdf).toHaveBeenCalledTimes(2));
  expect(
    await screen.findByRole("link", { name: "Mở bằng xác lập PDF" }),
  ).toBeDefined();
});
