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
        evidences={[
          {
            id: "evidence-1",
            mediaAssetId: "media-1",
            evidenceType: "SOURCE_DOCUMENT",
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
});
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
