import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CouncilVoteDialog } from "@/components/council/council-vote-dialog";

describe("CouncilVoteDialog", () => {
  it("requires a reason and asks for accessible final confirmation", async () => {
    const user = userEvent.setup();
    const vote = vi.fn().mockResolvedValue(undefined);
    render(<CouncilVoteDialog isPending={false} onVote={vote} />);

    await user.click(screen.getByRole("button", { name: "Biểu quyết hồ sơ" }));
    await user.click(screen.getByRole("button", { name: "Phê duyệt" }));
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra phiếu biểu quyết" }),
    );
    expect(
      screen.getByText("Vui lòng nêu lý do cho phiếu biểu quyết."),
    ).toBeDefined();

    await user.type(
      screen.getByLabelText("Lý do biểu quyết"),
      "Hồ sơ đáp ứng đầy đủ tiêu chí của Hội đồng.",
    );
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra phiếu biểu quyết" }),
    );
    expect(
      screen.getByRole("heading", { name: "Xác nhận phiếu biểu quyết" }),
    ).toBeDefined();

    await user.click(
      screen.getByRole("button", { name: "Xác nhận và gửi phiếu" }),
    );
    expect(vote).toHaveBeenCalledWith({
      choice: "APPROVE",
      reason: "Hồ sơ đáp ứng đầy đủ tiêu chí của Hội đồng.",
    });
  });
});
