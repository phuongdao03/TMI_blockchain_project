import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EvidenceViewer } from "@/components/reviews/evidence-viewer";

const signedUrl = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  mediaApi: { signedUrl },
}));
vi.mock("@/components/documents/private-document-verification", () => ({
  PrivateDocumentVerification: () => null,
}));

describe("EvidenceViewer", () => {
  it("previews a supported image in context with a short-lived link", async () => {
    const user = userEvent.setup();
    signedUrl.mockResolvedValue({
      url: "https://media.example.test/evidence.png",
      expiresAt: 1_800_000_000,
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <EvidenceViewer
          documentRules={[
            {
              key: "PRIMARY",
              label: "Nội dung chính",
              documentType: "SOURCE_DOCUMENT",
              required: false,
              allowedMimeTypes: ["image/png"],
              maxBytes: 10_000,
              maxCount: 10,
              defaultVisibility: "INTERNAL",
            },
          ]}
          evidences={[
            {
              id: "evidence-1",
              mediaAssetId: "media-1",
              evidenceType: "SOURCE_DOCUMENT",
              evidenceRole: "PRIMARY",
              title: "Ảnh bản gốc",
              description: "Ảnh đối chiếu nguồn gốc.",
              issuedAt: null,
              displayOrder: 1,
              isPublic: false,
              media: {
                mimeType: "image/png",
                bytes: 2_048,
                sha256: "a".repeat(64),
              },
            },
          ]}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Nội dung chính · 1 tệp")).toBeDefined();

    await user.click(screen.getByRole("button", { name: "Xem Ảnh bản gốc" }));

    expect(
      await screen.findByRole("region", { name: "Xem trước Ảnh bản gốc" }),
    ).toBeDefined();
    expect(
      screen.getByRole("img", { name: "Ảnh bản gốc" }).getAttribute("src"),
    ).toBe("https://media.example.test/evidence.png");
    await user.click(screen.getByRole("button", { name: "Đóng xem trước" }));
    expect(screen.queryByRole("img", { name: "Ảnh bản gốc" })).toBeNull();
  });

  it("shows the submitted document category and a readable file format", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <EvidenceViewer
          documentRules={[
            {
              key: "PRIMARY",
              label: "Nội dung chính",
              documentType: "SOURCE_DOCUMENT",
              required: false,
              allowedMimeTypes: ["video/mp4"],
              maxBytes: 10_000,
              maxCount: 10,
              defaultVisibility: "INTERNAL",
            },
          ]}
          evidences={[
            {
              id: "evidence-video",
              mediaAssetId: "media-video",
              evidenceType: "SOURCE_DOCUMENT",
              evidenceRole: "PRIMARY",
              title: "Video giới thiệu",
              description: null,
              issuedAt: null,
              displayOrder: 1,
              isPublic: false,
              media: {
                mimeType: "video/mp4",
                bytes: 2_048,
                sha256: "c".repeat(64),
              },
            },
          ]}
        />
      </QueryClientProvider>,
    );

    expect(screen.getByText("Loại tài liệu: Nội dung chính")).toBeDefined();
    expect(screen.getByText("Định dạng: MP4")).toBeDefined();
  });

  it("keeps a PDF out of an iframe and opens its signed link in a new tab", async () => {
    const user = userEvent.setup();
    signedUrl.mockResolvedValue({
      url: "https://media.example.test/evidence.pdf",
      expiresAt: 1_800_000_000,
    });
    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <EvidenceViewer
          evidences={[
            {
              id: "evidence-pdf",
              mediaAssetId: "media-pdf",
              evidenceType: "SOURCE_DOCUMENT",
              title: "Ho so PDF",
              description: null,
              issuedAt: null,
              displayOrder: 1,
              isPublic: false,
              media: {
                mimeType: "application/pdf",
                bytes: 2_048,
                sha256: "b".repeat(64),
              },
            },
          ]}
        />
      </QueryClientProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Xem Ho so PDF" }));

    expect(container.querySelector("iframe")).toBeNull();
    expect(screen.getByRole("link").getAttribute("href")).toBe(
      "https://media.example.test/evidence.pdf",
    );
  });
});
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
