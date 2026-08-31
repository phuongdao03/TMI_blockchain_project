import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FiveTScorecard } from "@/components/reviews/five-t-scorecard";

describe("FiveTScorecard", () => {
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
      screen.getByText("Tiếp theo: Chấm điểm và nhận xét tiêu chí Tính đúng đắn"),
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
    await user.selectOptions(screen.getByLabelText("Kiến nghị"), "APPROVE");

    await vi.waitFor(() => expect(save).toHaveBeenCalled(), {
      timeout: 2_000,
    });
    await user.click(
      screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
    );
    await vi.waitFor(() => expect(save).toHaveBeenCalledTimes(2));
    expect(
      screen.getByRole("heading", { name: "Xác nhận gửi kết quả" }),
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
