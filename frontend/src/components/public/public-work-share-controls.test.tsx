import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PublicWorkShareControls } from "@/components/public/public-work-share-controls";
import { publicApi } from "@/lib/api/client";
import type { PublicWorkDetail } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => ({
  publicApi: { recordShare: vi.fn() },
}));

vi.mock("@/lib/analytics/public-work-actions", () => ({
  emitPublicWorkAction: vi.fn(),
}));

const detail: PublicWorkDetail = {
  id: "03f15dce-f57b-4ec8-9960-1fefbd4ff307",
  slug: "public-work",
  title: "Public work",
  shortDescription: "A verified public work.",
  fullDescription: null,
  authorDisplayName: "TMI Studio",
  organizationDisplayName: null,
  categoryName: "Digital art",
  categorySlug: "digital-art",
  tags: [],
  publishedAt: "2026-08-04T00:00:00Z",
  visibility: "PUBLIC",
  certificate: null,
  proof: null,
  media: [],
  relatedWorks: [],
  canonicalSlug: "public-work",
  redirected: false,
};

const originalShare = navigator.share;

afterEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(navigator, "share", {
    configurable: true,
    value: originalShare,
  });
});

describe("PublicWorkShareControls", () => {
  it("records a copy-link intent only after clipboard success", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    vi.mocked(publicApi.recordShare).mockResolvedValue({ accepted: true });
    render(<PublicWorkShareControls detail={detail} />);

    const copyButton = screen.getAllByRole("button")[1];
    if (copyButton === undefined) throw new Error("Copy-link button is missing.");
    fireEvent.click(copyButton);

    await waitFor(() => {
      expect(publicApi.recordShare).toHaveBeenCalledWith(
        detail.canonicalSlug,
        "COPY_LINK",
      );
    });
  });

  it("records a native-share intent after the share sheet resolves", async () => {
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
    vi.mocked(publicApi.recordShare).mockResolvedValue({ accepted: true });
    render(<PublicWorkShareControls detail={detail} />);

    const nativeShareButton = screen.getAllByRole("button")[0];
    if (nativeShareButton === undefined) {
      throw new Error("Native-share button is missing.");
    }
    fireEvent.click(nativeShareButton);

    await waitFor(() => {
      expect(publicApi.recordShare).toHaveBeenCalledWith(
        detail.canonicalSlug,
        "NATIVE",
      );
    });
  });
});
