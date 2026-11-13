import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FeeManagementWorkspace } from "./fee-management-workspace";

const { feeApi, dossierApi, auth } = vi.hoisted(() => ({
  feeApi: {
    listPolicies: vi.fn(),
    listWaivers: vi.fn(),
    createPolicy: vi.fn(),
    approvePolicy: vi.fn(),
    cancelPolicy: vi.fn(),
    requestWaiver: vi.fn(),
    grantSubmissionWaiver: vi.fn(),
    decideWaiver: vi.fn(),
  },
  dossierApi: { listTypes: vi.fn() },
  auth: {
    user: {
      id: "admin-1",
      roles: ["ADMIN"],
      permissions: [
        "billing.fees.read",
        "billing.fees.policies.create",
        "billing.fees.policies.approve",
        "billing.fees.policies.cancel",
        "billing.fees.waivers.request",
        "billing.fees.waivers.approve",
        "payments.read",
        "payments.issue",
        "payments.reconcile",
      ],
    },
  },
}));

vi.mock("@/lib/api/client", () => ({
  feeApi,
  dossierApi,
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => auth.user,
}));
vi.mock("@/components/admin/payment-history-workspace", () => ({
  PaymentHistoryWorkspace: () => <div>Historial transactions</div>,
}));
vi.mock("@/components/admin/payment-request-workspace", () => ({
  PaymentRequestWorkspace: () => <div>Manual fee request</div>,
}));
vi.mock("@/components/admin/payment-order-reconciliation", () => ({
  PaymentOrderReconciliation: () => <div>Reconciliation queue</div>,
}));

function renderWorkspace() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <FeeManagementWorkspace />
    </QueryClientProvider>,
  );
}

describe("FeeManagementWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    auth.user.permissions = [
      "billing.fees.read",
      "billing.fees.policies.create",
      "billing.fees.policies.approve",
      "billing.fees.policies.cancel",
      "billing.fees.waivers.request",
      "billing.fees.waivers.approve",
      "payments.read",
      "payments.issue",
      "payments.reconcile",
    ];
    feeApi.listPolicies.mockResolvedValue([]);
    feeApi.listWaivers.mockResolvedValue([]);
    dossierApi.listTypes.mockResolvedValue([]);
  });

  it("shows the current fee first and groups legacy transaction operations", () => {
    const { container } = renderWorkspace();

    expect(container.querySelector("main")).toBeNull();
    expect(screen.getByText("Chưa có mức phí hiệu lực")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Thay đổi mức phí" }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Xem lịch sử" })).toBeTruthy();
    expect(screen.queryByRole("tablist")).toBeNull();
    fireEvent.click(screen.getByText("Giao dịch và đối soát hồ sơ legacy"));
    expect(screen.getByText("Historial transactions")).toBeTruthy();
    expect(screen.getByText("Reconciliation queue")).toBeTruthy();
    expect(
      screen.getByText(/Yêu cầu thu phí thủ công chỉ dành cho hồ sơ legacy/),
    ).toBeTruthy();
  });

  it("hides actions when the matching granular permission is absent", () => {
    auth.user.permissions = ["billing.fees.read"];
    renderWorkspace();

    expect(screen.getByText("Lịch sử phiên bản phí chung")).toBeTruthy();
    expect(
      screen.queryByRole("button", { name: "Thay đổi mức phí" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Tạo chính sách" })).toBeNull();
  });

  it("does not expose direct waiver administration to request-only accounts", () => {
    auth.user.permissions = ["billing.fees.waivers.request"];
    renderWorkspace();

    expect(screen.queryByText("Miễn phí hồ sơ thật")).toBeNull();
    expect(feeApi.listWaivers).not.toHaveBeenCalled();
    expect(screen.queryByText("Lịch sử phiên bản phí chung")).toBeNull();
  });

  it("lets an authorized Admin grant a full submission waiver directly", async () => {
    auth.user.permissions = ["billing.fees.waivers.approve"];
    feeApi.grantSubmissionWaiver.mockResolvedValue({});
    renderWorkspace();
    fireEvent.click(screen.getByText("Miễn phí hồ sơ thật"));

    fireEvent.change(screen.getByLabelText("Mã hồ sơ"), {
      target: { value: "dossier-1" },
    });
    fireEvent.change(screen.getByLabelText("Lý do"), {
      target: { value: "Approved by Admin" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Cấp miễn phí" }));

    await waitFor(() =>
      expect(feeApi.grantSubmissionWaiver).toHaveBeenCalledWith({
        dossierId: "dossier-1",
        reason: "Approved by Admin",
      }),
    );
  });

  it("requires an explicit confirmation before a single Admin activates a draft", async () => {
    const draft = {
      id: "policy-1",
      feeType: "DOSSIER_SUBMISSION",
      dossierTypeId: null,
      amountMinor: 5_000_000,
      currency: "VND",
      status: "DRAFT",
      displayName: "Phí nộp hồ sơ",
      reason: "Initial global submission fee",
      versionNo: 1,
      startsAt: "2026-11-13T00:00:00Z",
      endsAt: null,
      createdByUserId: "admin-1",
      approvedByUserId: null,
    };
    feeApi.listPolicies.mockResolvedValue([draft]);
    feeApi.approvePolicy.mockResolvedValue({ ...draft, status: "ACTIVE" });
    renderWorkspace();

    fireEvent.click(await screen.findByRole("button", { name: "Xem lại" }));
    expect(screen.getByText("Xem lại trước khi kích hoạt")).toBeTruthy();
    const confirm = screen.getByRole("button", { name: "Xác nhận kích hoạt" });
    expect(confirm).toHaveProperty("disabled", true);
    fireEvent.click(screen.getByRole("checkbox"));
    expect(confirm).toHaveProperty("disabled", false);
    fireEvent.click(confirm);

    await waitFor(() =>
      expect(feeApi.approvePolicy).toHaveBeenCalledWith("policy-1", true),
    );
  });
});
