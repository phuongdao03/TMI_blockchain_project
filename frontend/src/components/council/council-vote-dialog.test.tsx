import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CouncilVoteDialog } from "@/components/council/council-vote-dialog";

describe("CouncilVoteDialog", () => {
  it("requires a reason and asks for accessible final confirmation", async () => {
    const user = userEvent.setup();
    const vote = vi.fn().mockResolvedValue(undefined);
    render(<CouncilVoteDialog isPending={false} onVote={vote} />);

    await user.click(screen.getByRole("button", { name: "Gửi kết quả xử lý" }));
    await user.click(screen.getByRole("button", { name: "Phê duyệt" }));
    await user.click(screen.getByRole("button", { name: "Kiểm tra kết quả" }));
    expect(
      screen.getByText("Vui lòng nêu lý do cho kết quả đã chọn."),
    ).toBeDefined();

    await user.type(
      screen.getByLabelText("Lý do lựa chọn"),
      "Hồ sơ đáp ứng đầy đủ các tiêu chí xét duyệt.",
    );
    await user.click(screen.getByRole("button", { name: "Kiểm tra kết quả" }));
    expect(
      screen.getByRole("heading", { name: "Xác nhận kết quả xử lý" }),
    ).toBeDefined();

    await user.click(
      screen.getByRole("button", { name: "Xác nhận và gửi kết quả" }),
    );
    expect(vote).toHaveBeenCalledWith({
      choice: "APPROVE",
      reason: "Hồ sơ đáp ứng đầy đủ các tiêu chí xét duyệt.",
    });
  });
});
