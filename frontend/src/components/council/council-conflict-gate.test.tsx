import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CouncilConflictGate } from "@/components/council/council-conflict-gate";

describe("CouncilConflictGate", () => {
  it("requires a reason for a declared conflict", async () => {
    const user = userEvent.setup();
    const declare = vi.fn().mockResolvedValue(undefined);
    render(<CouncilConflictGate isPending={false} onDeclare={declare} />);

    await user.click(
      screen.getByRole("button", { name: "Tôi có xung đột lợi ích" }),
    );
    await user.click(screen.getByRole("button", { name: "Xác nhận xung đột" }));
    expect(screen.getByText("Vui lòng mô tả xung đột lợi ích.")).toBeDefined();

    await user.type(
      screen.getByLabelText("Lý do xung đột"),
      "Có quan hệ tài chính trực tiếp với chủ hồ sơ.",
    );
    await user.click(screen.getByRole("button", { name: "Xác nhận xung đột" }));
    expect(declare).toHaveBeenCalledWith({
      hasConflict: true,
      reason: "Có quan hệ tài chính trực tiếp với chủ hồ sơ.",
    });
  });
});
