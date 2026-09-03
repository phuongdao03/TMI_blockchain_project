import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FiveTScorecard } from "@/components/reviews/five-t-scorecard";

describe("FiveTScorecard", () => {
  it("uses evidence-based conclusions without a numeric total for new rubrics", () => {
    render(
      <FiveTScorecard
        evidences={[]}
        initialReview={null}
        isSaving={false}
        isSubmitting={false}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        readOnly={false}
        rubric={{
          version: "2026.2",
          title: "Kết luận hồ sơ",
          assessmentMethod: "VERDICT",
          gates: [],
          criteria: [
            {
              key: "identity",
              label: "Thông tin chủ thể",
              description: "Đối chiếu thông tin chủ thể trong hồ sơ.",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Kết luận theo tiêu chí")).toBeDefined();
    expect(screen.getByLabelText("Kết luận Thông tin chủ thể")).toBeDefined();
    expect(screen.queryByText("Tổng điểm tạm tính")).toBeNull();
  });

  it("derives a supplement result from criterion conclusions", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    const submit = vi.fn().mockResolvedValue(undefined);
    render(
      <FiveTScorecard
        evidences={[
          {
            id: "evidence-1",
            mediaAssetId: "a3fe0d4b-0b7d-45bc-8fc7-077dce2f8426",
            evidenceType: "SOURCE_DOCUMENT",
            evidenceRole: "PRIMARY",
            title: "Tài liệu giới thiệu",
            description: null,
            issuedAt: null,
            displayOrder: 1,
            isPublic: false,
            media: {
              mimeType: "application/pdf",
              bytes: 1024,
              sha256: "a".repeat(64),
            },
          },
        ]}
        initialReview={null}
        isSaving={false}
        isSubmitting={false}
        onSave={save}
        onSubmit={submit}
        readOnly={false}
        rubric={{
          version: "2026.2",
          title: "Kết luận hồ sơ",
          assessmentMethod: "VERDICT",
          gates: [],
          criteria: [
            {
              key: "evidence",
              label: "Tài liệu chứng minh",
              description: "Kiểm tra tài liệu đã nộp.",
            },
          ],
        }}
      />,
    );

    await user.selectOptions(
      screen.getByLabelText("Kết quả kiểm tra Tài liệu giới thiệu"),
      "VALID",
    );
    await user.selectOptions(
      screen.getByLabelText("Kết luận Tài liệu chứng minh"),
      "NEEDS_CLARIFICATION",
    );
    await user.type(
      screen.getByLabelText("Nhận định Tài liệu chứng minh"),
      "Tài liệu cần bổ sung ngày phát hành để có thể đối chiếu.",
    );
    await user.click(screen.getByRole("checkbox"));
    await user.type(
      screen.getByLabelText("Phản hồi gửi người nộp"),
      "Vui lòng bổ sung ngày phát hành của tài liệu.",
    );

    expect(screen.getByText("Yêu cầu bổ sung")).toBeDefined();
    await user.click(
      screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Xác nhận gửi kết quả" }),
    ).toBeDefined();
    expect(save).toHaveBeenCalledWith(
      expect.objectContaining({
        recommendation: "SUPPLEMENT",
        truthScore: null,
        criterionVerdicts: expect.objectContaining({
          evidence: expect.objectContaining({
            outcome: "NEEDS_CLARIFICATION",
          }),
        }),
      }),
    );
  });

  it("autosaves an incomplete gate explanation as a draft", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <FiveTScorecard
        evidences={[]}
        initialReview={null}
        isSaving={false}
        isSubmitting={false}
        onSave={save}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        readOnly={false}
        rubric={{
          version: "2026.2",
          title: "Kết luận hồ sơ",
          assessmentMethod: "VERDICT",
          gates: [
            {
              key: "eligibility",
              label: "Phạm vi tiếp nhận",
              description: "Kiểm tra hồ sơ thuộc phạm vi tiếp nhận.",
            },
          ],
          criteria: [
            {
              key: "evidence",
              label: "Tài liệu chứng minh",
              description: "Kiểm tra tài liệu đã nộp.",
            },
          ],
        }}
      />,
    );

    await user.type(
      screen.getByLabelText("Căn cứ Phạm vi tiếp nhận"),
      "Đang xem",
    );

    await vi.waitFor(
      () =>
        expect(save).toHaveBeenCalledWith(
          expect.objectContaining({
            gateAnswers: {
              eligibility: expect.objectContaining({
                outcome: "PASS",
                rationale: "Đang xem",
              }),
            },
          }),
        ),
      { timeout: 2_000 },
    );
  });

  it("validates all criteria, autosaves and confirms final submission", async () => {
    const user = userEvent.setup();
    const save = vi.fn().mockResolvedValue(undefined);
    const submit = vi.fn().mockResolvedValue(undefined);
    render(
      <FiveTScorecard
        evidences={[
          {
            id: "evidence-1",
            mediaAssetId: "a3fe0d4b-0b7d-45bc-8fc7-077dce2f8426",
            evidenceType: "SOURCE_DOCUMENT",
            title: "Bằng chứng nguồn gốc",
            description: null,
            issuedAt: null,
            displayOrder: 1,
            isPublic: false,
            media: {
              mimeType: "application/pdf",
              bytes: 1024,
              sha256: "a".repeat(64),
            },
          },
        ]}
        initialReview={null}
        isSaving={false}
        isSubmitting={false}
        onSave={save}
        onSubmit={submit}
        readOnly={false}
      />,
    );

    expect(screen.getByText("0/5 tiêu chí hoàn tất")).toBeDefined();
    expect(
      screen.getByText(
        "Tiếp theo: Chấm điểm và nhận xét tiêu chí Tính đúng đắn",
      ),
    ).toBeDefined();

    const truthScore = screen.getByLabelText("Điểm Tính đúng đắn");
    fireEvent.change(truthScore, { target: { value: "21" } });
    fireEvent.blur(truthScore);
    expect(await screen.findByText("Điểm phải từ 0 đến 20.")).toBeDefined();

    const criteria = [
      "Tính đúng đắn",
      "Tính minh bạch",
      "Quyền sở hữu & trách nhiệm",
      "Tính chuyên nghiệp",
      "Tính tôn trọng",
    ];
    for (const criterion of criteria) {
      const score = screen.getByLabelText(`Điểm ${criterion}`);
      fireEvent.change(score, { target: { value: "16" } });
      fireEvent.change(screen.getByLabelText(`Nhận xét ${criterion}`), {
        target: { value: `Nhận xét đầy đủ cho ${criterion}.` },
      });
    }
    for (const checkbox of screen.getAllByRole("checkbox")) {
      await user.click(checkbox);
    }
    await user.selectOptions(
      screen.getByLabelText("Kết quả kiểm tra Bằng chứng nguồn gốc"),
      "VALID",
    );
    await user.selectOptions(screen.getByLabelText("Kiến nghị"), "APPROVE");

    await vi.waitFor(() => expect(save).toHaveBeenCalled(), {
      timeout: 2_000,
    });
    await user.click(
      screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
    );
    expect(
      await screen.findByRole("heading", {
        name: "Xác nhận gửi kết quả",
      }),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Xác nhận gửi" }));
    expect(submit).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => {
      expect(
        screen.queryByRole("heading", { name: "Xác nhận gửi kết quả" }),
      ).toBeNull();
    });
  }, 10_000);
});
