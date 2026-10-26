import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";

const {
  candidateListMock,
  issueMock,
  listAdminOrdersMock,
  reconcileMock,
  waiveMock,
} = vi.hoisted(() => ({
  candidateListMock: vi.fn(),
  issueMock: vi.fn(),
  listAdminOrdersMock: vi.fn(),
  reconcileMock: vi.fn(),
  waiveMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  paymentApi: {
    issue: issueMock,
    listAdminOrders: listAdminOrdersMock,
    listCandidates: candidateListMock,
    reconcile: reconcileMock,
    waive: waiveMock,
  },
}));

function renderWorkspace(initialDossierId?: string) {
  candidateListMock.mockResolvedValue([
    {
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      dossierCode: "CNS-2026-C53E911EDDDA",
      dossierTitle: "Video chào mừng Tinh hoa Việt",
      versionNo: 2,
    },
  ]);
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <PaymentRequestWorkspace initialDossierId={initialDossierId} />
    </QueryClientProvider>,
  );
}

describe("PaymentRequestWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAdminOrdersMock.mockResolvedValue([]);
  });

  it("shows paid requests and confirmation time for administrative reconciliation", async () => {
    listAdminOrdersMock.mockResolvedValue([
      {
        order: {
          id: "paid-order",
          orderCode: "PAY-PAID-001",
          dossierId: "dossier-1",
          provider: "payos",
          providerOrderId: "provider-order",
          amountMinor: 2_000_000,
          currency: "VND",
          status: "PAID",
          expiresAt: "2026-10-20T08:00:00Z",
          paidAt: "2026-10-20T07:30:00Z",
          checkoutUrl: null,
          qrPayload: null,
          createdAt: "2026-10-20T07:00:00Z",
          updatedAt: "2026-10-20T07:30:00Z",
        },
        dossierCode: "THV-2026-0001",
        dossierTitle: "Hồ sơ thương hiệu",
      },
    ]);

    renderWorkspace();

    expect(
      await screen.findByRole("heading", {
        name: "Theo d\u00F5i thu ph\u00ED",
      }),
    ).toBeTruthy();
    expect(await screen.findByText(/PAY-PAID-001/)).toBeTruthy();
    expect(
      screen.getByText(
        "THV-2026-0001 \u00B7 H\u1ED3 s\u01A1 th\u01B0\u01A1ng hi\u1EC7u",
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(/\u0110\u00E3 ghi nh\u1EADn l\u00FAc/),
    ).toBeTruthy();
  });

  it("uses business language instead of payment provider implementation terms", () => {
    renderWorkspace();

    expect(screen.getByText("Thu phí hồ sơ")).toBeDefined();
    expect(screen.getByLabelText("Hồ sơ đã phê duyệt")).toBeDefined();
    expect(
      screen.queryByText(/PayOS|webhook|UUID|payments\.issue/i),
    ).toBeNull();
  });

  it("selects the approved dossier from the next-step link", async () => {
    renderWorkspace("9155dbf5-bb3e-449d-8bf0-9572cc642cac");
    await screen.findByRole("option", { name: /CNS-2026-C53E911EDDDA/ });
    expect(
      (screen.getByLabelText("Hồ sơ đã phê duyệt") as HTMLSelectElement).value,
    ).toBe("9155dbf5-bb3e-449d-8bf0-9572cc642cac");
  });

  it("does not submit an unknown dossier from the URL", async () => {
    renderWorkspace("unknown-dossier");
    await screen.findByRole("option", { name: /CNS-2026-C53E911EDDDA/ });
    fireEvent.change(screen.getByLabelText("Số phí cần thu (VND)"), {
      target: { value: "1500000" },
    });
    expect(
      (
        screen.getByRole("button", {
          name: "Gửi thông báo thu phí",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(issueMock).not.toHaveBeenCalled();
  });

  it("sends the operator-entered amount instead of a fixed frontend price", async () => {
    issueMock.mockResolvedValue({
      id: "payment-1",
      orderCode: "123456",
      amountMinor: 1_500_000,
      status: "PENDING",
    });
    renderWorkspace();

    await screen.findByRole("option", { name: /CNS-2026-C53E911EDDDA/ });
    fireEvent.change(await screen.findByLabelText("Hồ sơ đã phê duyệt"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.change(screen.getByLabelText("Số phí cần thu (VND)"), {
      target: { value: "1500000" },
    });
    await waitFor(() =>
      expect(
        (
          screen.getByRole("button", {
            name: "Gửi thông báo thu phí",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi thông báo thu phí" }),
    );

    await waitFor(() => expect(issueMock).toHaveBeenCalledOnce());
    expect(issueMock.mock.calls[0]?.[1]).toMatchObject({
      amountMinor: 1_500_000,
      currency: "VND",
      description: "Phí xác lập và phát hành bằng xác lập",
    });
    expect(
      await screen.findByText("Đã gửi yêu cầu thanh toán cho người nộp"),
    ).toBeTruthy();
  });

  it("reports that an adequately funded wallet was charged immediately", async () => {
    issueMock.mockResolvedValue({
      id: "payment-paid",
      orderCode: "123457",
      amountMinor: 1_500_000,
      status: "PAID",
    });
    renderWorkspace("9155dbf5-bb3e-449d-8bf0-9572cc642cac");

    await screen.findByRole("option", { name: /CNS-2026-C53E911EDDDA/ });
    fireEvent.change(screen.getByLabelText("Số phí cần thu (VND)"), {
      target: { value: "1500000" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi thông báo thu phí" }),
    );

    expect(await screen.findByText("Đã trừ phí từ ví người nộp")).toBeTruthy();
    expect(screen.getByText(/đã thanh toán bằng ví/)).toBeTruthy();
  });

  it("can waive the fee without creating a payment order", async () => {
    waiveMock.mockResolvedValue({
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      status: "PAID",
      reason: "Hồ sơ thuộc chương trình hỗ trợ miễn phí.",
    });
    renderWorkspace();

    await screen.findByText(/CNS-2026-C53E911EDDDA/);
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
    expect(
      await screen.findByText("Hồ sơ đã sẵn sàng để ghi nhận"),
    ).toBeTruthy();
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

    await screen.findByText(/CNS-2026-C53E911EDDDA/);
    fireEvent.change(await screen.findByLabelText("Hồ sơ đã phê duyệt"), {
      target: { value: "9155dbf5-bb3e-449d-8bf0-9572cc642cac" },
    });
    fireEvent.change(screen.getByLabelText("Số phí cần thu (VND)"), {
      target: { value: "1500000" },
    });
    await waitFor(() =>
      expect(
        (
          screen.getByRole("button", {
            name: "Gửi thông báo thu phí",
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(false),
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Gửi thông báo thu phí" }),
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
