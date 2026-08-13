import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PrivateDocumentVerification } from "@/components/documents/private-document-verification";

const verifyDocument = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  mediaApi: { verifyDocument },
}));

function renderVerification(mediaId: string) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <PrivateDocumentVerification mediaId={mediaId} />
    </QueryClientProvider>,
  );
}

describe("PrivateDocumentVerification", () => {
  it("occupies the full evidence grid width on narrow screens", () => {
    const { container } = renderVerification("media-id");

    expect(
      container.firstElementChild?.classList.contains("col-span-full"),
    ).toBe(true);
    expect(container.firstElementChild?.classList.contains("min-w-0")).toBe(
      true,
    );
  });

  it("explains a matching private document without exposing proof internals", async () => {
    verifyDocument.mockResolvedValue({
      status: "MATCH",
      checkedAt: "2026-08-12T08:00:00Z",
    });
    renderVerification("media-id");

    await userEvent.upload(
      screen.getByLabelText("Chọn bản tài liệu để kiểm tra"),
      new File(["hello"], "private.pdf"),
    );

    expect(await screen.findByText("Bản tài liệu trùng khớp")).toBeDefined();
    expect(
      screen.queryByText(/hash|database|role|rpc|private key/i),
    ).toBeNull();
  });

  it("gives safe next actions for pending and inaccessible documents", async () => {
    verifyDocument
      .mockResolvedValueOnce({
        status: "PENDING_CONFIRMATION",
        checkedAt: "2026-08-12T08:00:00Z",
      })
      .mockResolvedValueOnce({
        status: "NOT_AUTHORIZED",
        checkedAt: "2026-08-12T08:00:00Z",
      });
    const { rerender } = renderVerification("pending-id");
    await userEvent.upload(
      screen.getByLabelText("Chọn bản tài liệu để kiểm tra"),
      new File(["hello"], "private.pdf"),
    );
    expect(
      await screen.findByText("Bằng chứng đang được hoàn tất"),
    ).toBeDefined();

    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    });
    rerender(
      <QueryClientProvider client={queryClient}>
        <PrivateDocumentVerification mediaId="forbidden-id" />
      </QueryClientProvider>,
    );
    await userEvent.upload(
      screen.getByLabelText("Chọn bản tài liệu để kiểm tra"),
      new File(["hello"], "private.pdf"),
    );
    expect(
      await screen.findByText("Không thể kiểm tra tài liệu này"),
    ).toBeDefined();
  });
});
