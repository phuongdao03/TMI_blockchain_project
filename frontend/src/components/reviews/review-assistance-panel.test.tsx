import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReviewAssistancePanel } from "@/components/reviews/review-assistance-panel";

const requestAssistanceMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  reviewApi: { requestAssistance: requestAssistanceMock },
}));

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReviewAssistancePanel
        assignmentId="assignment-1"
        canRequest
        requests={[]}
      />
    </QueryClientProvider>,
  );
}

describe("ReviewAssistancePanel", () => {
  it("requires a meaningful reason and sends only the requested moderator count", async () => {
    const user = userEvent.setup();
    requestAssistanceMock.mockResolvedValue({ id: "request-1" });
    renderPanel();

    const send = screen.getByRole("button", { name: "Gửi Admin" });
    expect((send as HTMLButtonElement).disabled).toBe(true);

    await user.type(
      screen.getByLabelText("Lý do cần hỗ trợ"),
      "Cần chuyên gia cùng đối chiếu các bằng chứng chuyên ngành phức tạp.",
    );
    await user.selectOptions(
      screen.getByLabelText("Số moderator cần thêm"),
      "2",
    );
    await user.click(send);

    expect(requestAssistanceMock).toHaveBeenCalledWith("assignment-1", {
      reason:
        "Cần chuyên gia cùng đối chiếu các bằng chứng chuyên ngành phức tạp.",
      requestedReviewerCount: 2,
    });
  });
});
