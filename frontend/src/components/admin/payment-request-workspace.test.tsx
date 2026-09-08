import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";

const { candidateListMock, issueMock, waiveMock } = vi.hoisted(() => ({
  candidateListMock: vi.fn(),
  issueMock: vi.fn(),
  waiveMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: {
    issue: issueMock,
    listCandidates: candidateListMock,
    waive: waiveMock,
  },
}));

function renderWorkspace() {
  candidateListMock.mockResolvedValue([
    {
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      dossierCode: "TMI-2026-C53E911EDDDA",
      dossierTitle: "Video chào mừng Tinh hoa Việt",
      versionNo: 2,
    },
  ]);
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <PaymentRequestWorkspace />
    </QueryClientProvider>,
  );
}

describe("PaymentRequestWorkspace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses business language instead of payment provider implementation terms", () => {
    renderWorkspace();

    expect(screen.getByText("Quyết định phí hồ sơ")).toBeDefined();
    expect(screen.getByLabelText("Hồ sơ đã phê duyệt")).toBeDefined();
    expect(
      screen.queryByText(/PayOS|webhook|UUID|payments\.issue/i),
    ).toBeNull();
  });

  it("sends the operator-entered amount instead of a fixed frontend price", async () => {
    issueMock.mockResolvedValue({
      id: "payment-1",
      orderCode: "123456",
      amountMinor: 1_500_000,
    });
    renderWorkspace();

    await screen.findByText(/TMI-2026-C53E911EDDDA/);
    fireEvent.change(await screen.findByLabelText("Hồ sơ đã phê duyệt"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.change(screen.getByLabelText("Số tiền cần thanh toán (VND)"), {
      target: { value: "1500000" },
    });
    await waitFor(() =>
      expect(
        (
          screen.getByRole("button", {
            name: "Gửi yêu cầu thanh toán",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi yêu cầu thanh toán" }),
    );

    await waitFor(() => expect(issueMock).toHaveBeenCalledOnce());
    expect(issueMock.mock.calls[0]?.[1]).toMatchObject({
      amountMinor: 1_500_000,
      currency: "VND",
      description: "Phí xác lập và phát hành chứng thư",
    });
    expect(
      await screen.findByText("Đã gửi yêu cầu cho người nộp"),
    ).toBeTruthy();
  });

  it("can waive the fee without creating a payment order", async () => {
    waiveMock.mockResolvedValue({
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      status: "PAID",
      reason: "Hồ sơ thuộc chương trình hỗ trợ miễn phí.",
    });
    renderWorkspace();

    await screen.findByText(/TMI-2026-C53E911EDDDA/);
    fireEvent.change(await screen.findByLabelText("Hồ sơ đã phê duyệt"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.click(screen.getByRole("radio", { name: "Miễn phí" }));
    await waitFor(() =>
      expect(
        (screen.getByRole("radio", { name: "Miễn phí" }) as HTMLInputElement)
          .checked,
      ).toBe(true),
    );
    fireEvent.change(screen.getByLabelText("Lý do miễn phí"), {
      target: { value: "Hồ sơ thuộc chương trình hỗ trợ miễn phí." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận miễn phí" }));

    await waitFor(() => expect(waiveMock).toHaveBeenCalledOnce());
    expect(issueMock).not.toHaveBeenCalled();
    expect(await screen.findByText("Hồ sơ đã sẵn sàng để ký")).toBeTruthy();
  });

  it("rotates the idempotency key when the operator starts another decision", async () => {
    issueMock.mockResolvedValue({
      id: "payment-1",
      orderCode: "123456",
      amountMinor: 1_500_000,
    });
    waiveMock.mockResolvedValue({
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      status: "PAID",
      reason: "Hồ sơ thuộc chương trình hỗ trợ miễn phí.",
    });
    renderWorkspace();

    await screen.findByText(/TMI-2026-C53E911EDDDA/);
    fireEvent.change(await screen.findByLabelText("Hồ sơ đã phê duyệt"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.change(screen.getByLabelText("Số tiền cần thanh toán (VND)"), {
      target: { value: "1500000" },
    });
    await waitFor(() =>
      expect(
        (
          screen.getByRole("button", {
            name: "Gửi yêu cầu thanh toán",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi yêu cầu thanh toán" }),
    );
    await waitFor(() => expect(issueMock).toHaveBeenCalledOnce());

    fireEvent.click(screen.getByRole("radio", { name: "Miễn phí" }));
    fireEvent.change(screen.getByLabelText("Lý do miễn phí"), {
      target: { value: "Hồ sơ thuộc chương trình hỗ trợ miễn phí." },
    });
    await waitFor(() =>
      expect(
        (
          screen.getByRole("button", {
            name: "Xác nhận miễn phí",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    );
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận miễn phí" }));
    await waitFor(() => expect(waiveMock).toHaveBeenCalledOnce());

    expect(issueMock.mock.calls[0]?.[2]).not.toBe(waiveMock.mock.calls[0]?.[2]);
  });
});
