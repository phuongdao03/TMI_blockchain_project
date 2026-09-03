import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CouncilConflictGate } from "@/components/council/council-conflict-gate";

describe("CouncilConflictGate", () => {
  it("lets an internal reviewer accept the dossier without conflict language", async () => {
    const user = userEvent.setup();
    const declare = vi.fn().mockResolvedValue(undefined);
    render(<CouncilConflictGate isPending={false} onDeclare={declare} />);

    expect(screen.queryByText(/xung đột/i)).toBeNull();
    await user.click(screen.getByRole("button", { name: "Tiếp nhận hồ sơ" }));
    expect(declare).toHaveBeenCalledWith({
      hasConflict: false,
      reason: null,
    });
  });
});
