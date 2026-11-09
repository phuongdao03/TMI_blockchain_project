import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
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
    feeApi.listPolicies.mockResolvedValue([]);
    feeApi.listWaivers.mockResolvedValue([]);
    dossierApi.listTypes.mockResolvedValue([]);
  });

  it("offers the four fee operations and keeps reconciliation separate", () => {
    const { container } = renderWorkspace();

    expect(container.querySelector("main")).toBeNull();

    expect(screen.getByRole("tab", { name: "Giao dịch" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Miễn giảm" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Chính sách" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Đối soát" })).toBeTruthy();
    expect(screen.getByText("Historial transactions")).toBeTruthy();

    fireEvent.click(screen.getByRole("tab", { name: "Đối soát" }));
    expect(screen.getByText("Reconciliation queue")).toBeTruthy();
  });

  it("hides actions when the matching granular permission is absent", () => {
    auth.user.permissions = ["billing.fees.read"];
    renderWorkspace();

    expect(screen.getByRole("tab", { name: "Chính sách" })).toBeTruthy();
    expect(screen.queryByRole("tab", { name: "Giao dịch" })).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Chính sách" }));
    expect(screen.queryByRole("button", { name: "Tạo chính sách" })).toBeNull();
  });

  it("lets waiver requesters submit without exposing other waiver records", () => {
    auth.user.permissions = ["billing.fees.waivers.request"];
    renderWorkspace();

    expect(screen.getByRole("tab", { name: "Miễn giảm" })).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Đề nghị miễn giảm" }),
    ).toBeTruthy();
    expect(feeApi.listWaivers).not.toHaveBeenCalled();
    expect(screen.queryByRole("tab", { name: "Chính sách" })).toBeNull();
  });
});
