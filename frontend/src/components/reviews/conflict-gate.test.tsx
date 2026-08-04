import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConflictGate } from "@/components/reviews/conflict-gate";

describe("ConflictGate", () => {
  it("requires a reason for a conflict and supports acknowledgement", async () => {
    const user = userEvent.setup();
    const declare = vi.fn().mockResolvedValue(undefined);
    render(<ConflictGate isPending={false} onDeclare={declare} />);

    await user.click(
      screen.getByRole("button", { name: "Tôi có xung đột lợi ích" }),
    );
    await user.click(screen.getByRole("button", { name: "Xác nhận xung đột" }));
    expect(screen.getByText("Vui lòng mô tả xung đột lợi ích.")).toBeDefined();

    await user.type(
      screen.getByLabelText("Lý do xung đột"),
      "Đã từng tư vấn cho chủ hồ sơ.",
    );
    await user.click(screen.getByRole("button", { name: "Xác nhận xung đột" }));
    expect(declare).toHaveBeenCalledWith({
      hasConflict: true,
      reason: "Đã từng tư vấn cho chủ hồ sơ.",
    });
  });
});
