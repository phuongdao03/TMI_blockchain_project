import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DossierWorkspace } from "@/components/dossiers/dossier-workspace";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  update: vi.fn(),
  attachEvidence: vi.fn(),
  removeEvidence: vi.fn(),
  submit: vi.fn(),
  resubmit: vi.fn(),
  versions: vi.fn(),
  timeline: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({ dossierApi: api }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const dossier = {
  id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
  code: "TMI-2026-ABCDEF123456",
  ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
  organizationId: null,
  categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
  title: "Bộ nhận diện TMI",
  slug: null,
  summary: "Hồ sơ quyền sở hữu.",
  status: "DRAFT" as const,
  visibility: "PRIVATE" as const,
  currentVersionNo: 0,
  submittedAt: null,
  createdAt: "2026-07-31T08:00:00Z",
  updatedAt: "2026-07-31T08:00:00Z",
  canEdit: true,
  evidences: [
    {
      id: "5f81fa20-ec0a-4393-a90c-bf9c6285766d",
      dossierId: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      dossierVersionId: null,
      mediaAssetId: "6a0bb388-3c26-4417-aed8-3ca05c212d1f",
      evidenceType: "OWNERSHIP_DOCUMENT",
      title: "Giấy xác nhận quyền sở hữu",
      description: null,
      issuedAt: null,
      displayOrder: 0,
      isPublic: false,
      mimeType: "application/pdf",
      bytes: 2048,
      sha256: "a".repeat(64),
    },
  ],
};

describe("DossierWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("autosaves draft information and submits a complete dossier", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue(dossier);
    api.update.mockResolvedValue(dossier);
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submit.mockResolvedValue({
      dossier: { ...dossier, status: "SUBMITTED", canEdit: false },
      version: { id: "version-1" },
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Bộ nhận diện TMI",
      }),
    ).toBeDefined();
    await user.clear(screen.getByLabelText("Tên hồ sơ"));
    await user.type(screen.getByLabelText("Tên hồ sơ"), "Bộ nhận diện mới");
    await vi.waitFor(
      () => {
        expect(api.update.mock.calls[0]?.[0]).toBe(dossier.id);
        expect(api.update.mock.calls[0]?.[1]).toEqual(
          expect.objectContaining({ title: "Bộ nhận diện mới" }),
        );
      },
      { timeout: 2000 },
    );

    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(screen.getByText("Giấy xác nhận quyền sở hữu")).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Nộp hồ sơ" }));
    expect(api.submit.mock.calls[0]?.[0]).toBe(dossier.id);
    expect(api.submit.mock.calls[0]?.[1]).toEqual(expect.any(String));
  });

  it("does not start another autosave while the current request is pending", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue(dossier);
    api.update.mockReturnValue(new Promise(() => undefined));
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    const title = await screen.findByLabelText("Tên hồ sơ");
    await user.clear(title);
    await user.type(title, "Bộ nhận diện đang lưu");

    await vi.waitFor(() => expect(api.update).toHaveBeenCalledTimes(1), {
      timeout: 2000,
    });
    await new Promise((resolve) => window.setTimeout(resolve, 850));

    expect(api.update).toHaveBeenCalledTimes(1);
  });

  it("explains and enforces read-only submitted state", async () => {
    api.get.mockResolvedValue({
      ...dossier,
      status: "SUBMITTED",
      canEdit: false,
    });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("Hồ sơ đã nộp và đang ở chế độ chỉ đọc."),
    ).toBeDefined();
    expect(screen.getByLabelText("Tên hồ sơ").hasAttribute("disabled")).toBe(
      true,
    );
  });
});
