import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewEvidenceAssessments } from "@/components/reviews/review-evidence-assessments";

const evidence = {
  id: "evidence-1",
  mediaAssetId: "media-1",
  evidenceType: "PRIMARY",
  evidenceRole: "PRIMARY",
  title: "Video giới thiệu tác phẩm",
  description: null,
  issuedAt: null,
  displayOrder: 1,
  isPublic: false,
  media: {
    mimeType: "video/mp4",
    bytes: 2_048,
    sha256: "a".repeat(64),
  },
};

describe("ReviewEvidenceAssessments", () => {
  it("keeps relevance separate from content verification without preset success", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ReviewEvidenceAssessments
        assessments={{}}
        evidences={[evidence]}
        onChange={onChange}
      />,
    );
    const verification = screen.getByRole("combobox", {
      name: "Kiểm chứng nội dung Video giới thiệu tác phẩm",
    });
    expect(verification).toHaveProperty("value", "UNVERIFIED");
    await user.selectOptions(verification, "PARTIAL");
    expect(onChange.mock.calls.at(-1)?.[0]["media-1"]).toMatchObject({
      status: "UNREVIEWED",
      verification: {
        outcome: "PARTIAL",
        method: "",
        source: "",
        scope: "",
        limitations: "",
      },
    });
  });

  it("shows incomplete verification fields and locks them for submitted reports", () => {
    render(
      <ReviewEvidenceAssessments
        assessments={{
          "media-1": {
            status: "VALID",
            note: "",
            verification: {
              outcome: "PARTIAL",
              method: "",
              source: "",
              scope: "",
              limitations: "",
            },
          },
        }}
        evidences={[evidence]}
        onChange={vi.fn()}
        readOnly
      />,
    );
    for (const label of [
      "Phương pháp đối chiếu",
      "Nguồn đối chiếu",
      "Phạm vi đã kiểm tra",
      "Giới hạn kiểm chứng",
    ]) {
      expect(
        screen.getByRole("textbox", {
          name: `${label} — Video giới thiệu tác phẩm`,
        }),
      ).toHaveProperty("disabled", true);
    }
  });

  it("records a clear status for each frozen file", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ReviewEvidenceAssessments
        assessments={{}}
        evidences={[evidence]}
        onChange={onChange}
      />,
    );

    expect(screen.getByText("Định dạng MP4")).toBeDefined();

    await user.selectOptions(
      screen.getByLabelText("Kết quả kiểm tra Video giới thiệu tác phẩm"),
      "VALID",
    );

    expect(onChange).toHaveBeenCalledWith({
      "media-1": { status: "VALID", note: "" },
    });
  });

  it("asks for an explanation when clarification is needed", () => {
    render(
      <ReviewEvidenceAssessments
        assessments={{
          "media-1": { status: "NEEDS_CLARIFICATION", note: "" },
        }}
        evidences={[evidence]}
        onChange={vi.fn()}
      />,
    );

    expect(
      screen.getByLabelText("Nội dung cần khách hàng làm rõ"),
    ).toBeDefined();
  });
});
