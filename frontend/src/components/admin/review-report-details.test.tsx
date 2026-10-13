import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReviewReportDetails } from "@/components/admin/review-report-details";
import type { ReviewData, ReviewSnapshot } from "@/lib/api/types";

const snapshot = {
  schemaVersion: 2,
  dossier: { id: "dossier-1", code: "HS-1", title: "Hồ sơ" },
  evidences: [
    {
      id: "evidence-1",
      mediaAssetId: "media-1",
      evidenceType: "SOURCE_DOCUMENT",
      title: "Tệp nguồn gốc",
      description: null,
      issuedAt: null,
      displayOrder: 0,
      isPublic: false,
      media: {
        mimeType: "application/pdf",
        bytes: 1024,
        sha256: "a".repeat(64),
      },
    },
  ],
} satisfies ReviewSnapshot;

describe("ReviewReportDetails", () => {
  it("shows a legacy 5T comment and its cited file", () => {
    const review = {
      truthScore: 16,
      criterionComments: { truth: "Nguồn gốc đã được đối chiếu với tệp gốc." },
      criterionEvidence: { truth: ["media-1"] },
    } as unknown as ReviewData;
    render(<ReviewReportDetails review={review} snapshot={snapshot} />);

    expect(screen.getByText("Tính đúng đắn")).toBeTruthy();
    expect(screen.getByText("16/20 điểm")).toBeTruthy();
    expect(
      screen.getByText("Nguồn gốc đã được đối chiếu với tệp gốc."),
    ).toBeTruthy();
    expect(screen.getByText(/Tài liệu dẫn chiếu: Tệp nguồn gốc/)).toBeTruthy();
  });

  it("shows specialist and gate reasoning alongside 5T when present", () => {
    const scoredSnapshot: ReviewSnapshot = {
      ...snapshot,
      dossier: {
        ...snapshot.dossier,
        dossierType: {
          reviewRubric: {
            version: "2026.2",
            title: "Tiêu chí chuyên môn",
            assessmentMethod: "SCORED",
            gates: [
              {
                key: "eligible",
                label: "Điều kiện tiếp nhận",
                description: "Kiểm tra điều kiện.",
              },
            ],
            criteria: [
              {
                key: "origin",
                label: "Nguồn gốc chuyên môn",
                description: "Kiểm tra nguồn gốc.",
                weight: 100,
              },
            ],
          },
        },
      },
    };
    const review = {
      gateAnswers: {
        eligible: {
          outcome: "PASS",
          rationale: "Điều kiện tiếp nhận đã được xác minh.",
          evidenceMediaIds: ["media-1"],
        },
      },
      specialistAnswers: {
        origin: {
          score: 4,
          rationale: "Nguồn gốc chuyên môn được xác thực.",
          evidenceMediaIds: ["media-1"],
        },
      },
      truthScore: 15,
      criterionComments: { truth: "Nội dung 5T đã được kiểm chứng." },
      criterionEvidence: { truth: ["media-1"] },
    } as unknown as ReviewData;
    render(<ReviewReportDetails review={review} snapshot={scoredSnapshot} />);

    expect(screen.getByText("Điều kiện tiếp nhận")).toBeTruthy();
    expect(screen.getByText("Nguồn gốc chuyên môn")).toBeTruthy();
    expect(screen.getByText("4/5 điểm")).toBeTruthy();
    expect(screen.getByText("5T · Tính đúng đắn")).toBeTruthy();
    expect(screen.getByText("Nội dung 5T đã được kiểm chứng.")).toBeTruthy();
  });
});
