import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { AuditWorkspace } from "@/components/admin/audit-workspace";
import { auditApi } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  auditApi: {
    list: vi.fn(async () => ({
      success: true,
      data: [
        {
          id: "audit-1",
          actorUserId: null,
          actorType: "SERVICE",
          actorService: "certificate-worker",
          action: "certificate.version.approved",
          resourceType: "certificate",
          resourceId: "CERT-001",
          before: null,
          after: { status: "ACTIVE" },
          requestId: "request-1",
          integrityStatus: "VERIFIED",
          retentionUntil: "2033-08-01T00:00:00Z",
          createdAt: "2026-08-11T02:00:00Z",
        },
      ],
      meta: { page: 1, pageSize: 20, total: 1 },
    })),
    checkIntegrity: vi.fn(async () => ({
      scanned: 10,
      total: 10,
      isComplete: true,
      counts: {
        VERIFIED: 9,
        TAMPERED: 1,
        UNSEALED: 0,
        KEY_UNAVAILABLE: 0,
      },
    })),
  },
}));

function Wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {children}
    </QueryClientProvider>
  );
}

describe("AuditWorkspace", () => {
  it("presents an operational history without exposing internal role or storage details", async () => {
    render(<AuditWorkspace />, { wrapper: Wrapper });

    expect(await screen.findByText("Lịch sử vận hành")).toBeDefined();
    expect(screen.getByText("Tính toàn vẹn bản ghi")).toBeDefined();
    expect(
      screen
        .getByRole("link", { name: "Tải báo cáo CSV" })
        .getAttribute("href"),
    ).toContain("/api/v1/admin/audit/exports.csv");
    expect(await screen.findByText("Đã kiểm chứng")).toBeDefined();
    expect(screen.queryByText(/REVIEWER|COUNCIL|database|schema/i)).toBeNull();
  });

  it("applies task-oriented filters and reports integrity exceptions", async () => {
    const user = userEvent.setup();
    render(<AuditWorkspace />, { wrapper: Wrapper });

    await screen.findByText("Đã kiểm chứng");
    await user.selectOptions(
      screen.getByLabelText("Loại hoạt động"),
      "dossier.approved",
    );
    await waitFor(() =>
      expect(auditApi.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ action: "dossier.approved" }),
      ),
    );

    await user.click(screen.getByRole("button", { name: "Kiểm tra ngay" }));
    expect(await screen.findByText("1 bản ghi cần xử lý")).toBeDefined();
    expect(auditApi.checkIntegrity).toHaveBeenCalledWith(10_000);
  });

  it("does not present a bounded integrity scan as a complete result", async () => {
    vi.mocked(auditApi.checkIntegrity).mockResolvedValueOnce({
      scanned: 10,
      total: 20,
      isComplete: false,
      counts: {
        VERIFIED: 10,
        TAMPERED: 0,
        UNSEALED: 0,
        KEY_UNAVAILABLE: 0,
      },
    });
    const user = userEvent.setup();
    render(<AuditWorkspace />, { wrapper: Wrapper });

    await user.click(
      await screen.findByRole("button", { name: "Kiểm tra ngay" }),
    );
    expect(
      await screen.findByText("Phạm vi kiểm tra chưa đầy đủ (10/20 bản ghi)"),
    ).toBeDefined();
    expect(screen.queryByText("Không phát hiện bất thường")).toBeNull();
  });
});
