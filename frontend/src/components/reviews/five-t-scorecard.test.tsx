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
        initialReview={null}
        isSaving={false}
        isSubmitting={false}
        onSave={save}
        onSubmit={submit}
        readOnly={false}
      />,
    );

    const truthScore = screen.getByLabelText("Điểm Tính đúng đắn");
    fireEvent.change(truthScore, { target: { value: "21" } });
    fireEvent.blur(truthScore);
    expect(await screen.findByText("Điểm phải từ 0 đến 20.")).toBeDefined();

    const criteria = [
      "Tính đúng đắn",
      "Tính minh bạch",
      "Tinh thần trách nhiệm",
      "Tính chuyên nghiệp",
      "Sự tôn trọng",
    ];
    for (const criterion of criteria) {
      const score = screen.getByLabelText(`Điểm ${criterion}`);
      fireEvent.change(score, { target: { value: "16" } });
      fireEvent.change(screen.getByLabelText(`Nhận xét ${criterion}`), {
        target: { value: `Nhận xét đầy đủ cho ${criterion}.` },
      });
    }
    await user.selectOptions(screen.getByLabelText("Kiến nghị"), "APPROVE");

    await vi.waitFor(() => expect(save).toHaveBeenCalled(), {
      timeout: 2_000,
    });
    await user.click(
      screen.getByRole("button", { name: "Gửi kết quả thẩm định" }),
    );
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
