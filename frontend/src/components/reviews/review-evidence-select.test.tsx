import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewEvidenceSelect } from "@/components/reviews/review-evidence-select";
import type { ReviewEvidenceSnapshot } from "@/lib/api/types";

const evidences: ReviewEvidenceSnapshot[] = [
  {
    id: "evidence-1",
    mediaAssetId: "media-1",
    evidenceType: "RIGHTS",
    title: "Bằng chứng về quyền sử dụng nhãn hiệu và phạm vi đại diện",
    description: null,
    issuedAt: null,
    displayOrder: 0,
    isPublic: false,
    media: { mimeType: "application/pdf", bytes: 2048, sha256: "a".repeat(64) },
  },
  {
    id: "evidence-2",
    mediaAssetId: "media-2",
    evidenceType: "PRIMARY",
    title: "Hình ảnh sản phẩm và thông tin đối chiếu",
    description: null,
    issuedAt: null,
    displayOrder: 1,
    isPublic: false,
    media: { mimeType: "image/png", bytes: 4096, sha256: "b".repeat(64) },
  },
];

describe("ReviewEvidenceSelect", () => {
  it("shows each document title and format without assuming an ownership certificate", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender } = render(
      <ReviewEvidenceSelect
        disabled={false}
        evidences={evidences}
        label="Thông tin nhất quán"
        onChange={onChange}
        value={[]}
      />,
    );

    expect(screen.getByText("Định dạng PDF")).toBeDefined();
    expect(screen.getByText("Định dạng PNG")).toBeDefined();
    await user.click(screen.getByText(evidences[0]!.title));
    expect(onChange).toHaveBeenLastCalledWith(["media-1"]);

    rerender(
      <ReviewEvidenceSelect
        disabled={false}
        evidences={evidences}
        label="Thông tin nhất quán"
        onChange={onChange}
        value={["media-1"]}
      />,
    );
    await user.click(screen.getByText(evidences[1]!.title));
    expect(onChange).toHaveBeenLastCalledWith(["media-1", "media-2"]);
  });
});
