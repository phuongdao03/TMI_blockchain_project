import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DeferredProposalViewer } from "@/components/public/deferred-proposal-viewer";

vi.mock("@/components/public/proposal-viewer", () => ({
  ProposalViewer: () => <div>Trình đọc proposal đã sẵn sàng</div>,
}));

describe("DeferredProposalViewer", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the heavy reader only when its section approaches the viewport", async () => {
    let notify: IntersectionObserverCallback = () => {};
    const disconnect = vi.fn();
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        constructor(callback: IntersectionObserverCallback) {
          notify = callback;
        }
        observe() {}
        disconnect = disconnect;
      },
    );

    render(<DeferredProposalViewer />);
    expect(screen.getByText("Đang chuẩn bị trình đọc tài liệu…")).toBeDefined();
    expect(screen.queryByText("Trình đọc proposal đã sẵn sàng")).toBeNull();

    act(() =>
      notify(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      ),
    );
    await waitFor(() =>
      expect(screen.getByText("Trình đọc proposal đã sẵn sàng")).toBeDefined(),
    );
    expect(disconnect).toHaveBeenCalled();
  });
});
