import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
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
  code: "CNS-2026-ABCDEF123456",
  ownerUserId: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
  organizationId: null,
  categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
  dossierTypeId: "9e1a095a-0cbd-4f3d-8e24-93b1771ec8b7",
  dossierTypeVersionId: "2ece72a5-06d8-4200-8a0c-dc7f7ab7bf40",
  formData: {},
  title: "Bộ nhận diện CNS",
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
      evidenceRole: "OWNERSHIP_DOCUMENT",
      accessScope: "INTERNAL",
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
  documentRules: [
    {
      key: "OWNERSHIP_DOCUMENT",
      label: "Tài liệu quyền sở hữu",
      documentType: "OWNERSHIP_DOCUMENT",
      required: true,
      allowedMimeTypes: ["application/pdf"],
      maxBytes: 31_457_280,
      maxCount: 1,
      defaultVisibility: "INTERNAL",
    },
  ],
};

describe("DossierWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("confirms a newly created draft and opens the evidence step", async () => {
    api.get.mockResolvedValue({ ...dossier, evidences: [] });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} justCreated />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Đã tạo hồ sơ nháp")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Thêm tài liệu" }).getAttribute("href"),
    ).toBe("#dossier-steps");
    expect(screen.getByText("Tài liệu cho hồ sơ của bạn")).toBeTruthy();
  });

  it("autosaves draft information and submits a complete dossier", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue(dossier);
    api.update.mockResolvedValue(dossier);
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submit.mockResolvedValue({
      dossier: { ...dossier, status: "SUBMITTED", canEdit: false },
      version: { id: "version-1", submittedAt: "2026-07-31T09:00:00Z" },
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
        name: "Bộ nhận diện CNS",
      }),
    ).toBeDefined();
    expect(screen.getByText("Hồ sơ đang được bạn chuẩn bị.")).toBeDefined();
    expect(screen.getByRole("status").className).toContain(
      "dossier-autosave-status",
    );
    expect(
      screen.queryByText(/SHA-256|snapshot|blockchain|database|backend/i),
    ).toBeNull();
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
    expect(
      await screen.findByText("Hồ sơ đã được gửi thành công"),
    ).toBeDefined();
    expect(
      screen.getByText("Bước tiếp theo: Tinh Hoa Việt kiểm tra hồ sơ của bạn."),
    ).toBeDefined();
    const nextSteps = screen.getByRole("list", {
      name: "Các bước sau khi nộp",
    });
    expect(within(nextSteps).getByText("1. Đã tiếp nhận")).toBeTruthy();
    expect(within(nextSteps).getByText("2. Kiểm duyệt hồ sơ")).toBeTruthy();
    expect(within(nextSteps).getByText("3. Thông báo kết quả")).toBeTruthy();
    expect(
      screen.getByRole("link", { name: "Xem thông báo" }).getAttribute("href"),
    ).toBe("/notifications");
    expect(
      screen
        .getByRole("link", { name: "Về hồ sơ của tôi" })
        .getAttribute("href"),
    ).toBe("/dossiers");
  });

  it("shows the latest supplement request in the next-action panel", async () => {
    api.get.mockResolvedValue({
      ...dossier,
      status: "NEEDS_SUPPLEMENT",
      canEdit: true,
    });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([
      {
        id: "history-1",
        toStatus: "NEEDS_SUPPLEMENT",
        note: "Bổ sung giấy xác nhận quyền sở hữu.",
        createdAt: "2026-08-01T00:00:00Z",
      },
    ]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(
        "Nội dung cần bổ sung: Bổ sung giấy xác nhận quyền sở hữu.",
      ),
    ).toBeDefined();
  });

  it("reopens editing when a submitted dossier later needs a supplement", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue(dossier);
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submit.mockResolvedValue({
      dossier: { ...dossier, status: "SUBMITTED", canEdit: false },
      version: { id: "version-1", submittedAt: "2026-07-31T09:00:00Z" },
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    await screen.findByLabelText("Tên hồ sơ");
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    await user.click(screen.getByRole("button", { name: "Nộp hồ sơ" }));
    await screen.findByText("Hồ sơ đã được gửi thành công");

    api.get.mockResolvedValue({
      ...dossier,
      status: "NEEDS_SUPPLEMENT",
      canEdit: true,
    });
    await queryClient.invalidateQueries();

    expect(
      await screen.findByRole("button", { name: "Tiếp tục hoàn thiện" }),
    ).toBeDefined();
    expect(screen.queryByText("Hồ sơ đã được gửi thành công")).toBeNull();
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
    expect(
      screen.getByRole("button", { name: /Kiểm tra & nộp/ }),
    ).toHaveProperty("disabled", true);
    expect(api.submit).not.toHaveBeenCalled();
  });

  it("keeps newer edits made while an earlier autosave is pending", async () => {
    const user = userEvent.setup();
    let finishFirstSave!: (value: typeof dossier) => void;
    api.get.mockResolvedValue(dossier);
    api.update
      .mockImplementationOnce(
        () =>
          new Promise<typeof dossier>((resolve) => {
            finishFirstSave = resolve;
          }),
      )
      .mockImplementation(async (_id: string, values: { title: string }) => ({
        ...dossier,
        ...values,
      }));
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    const title = await screen.findByLabelText("Tên hồ sơ");
    await user.clear(title);
    await user.type(title, "Tên ban đầu");
    await vi.waitFor(() => expect(api.update).toHaveBeenCalledTimes(1), {
      timeout: 2000,
    });
    await user.type(title, " tiếp theo");
    finishFirstSave({ ...dossier, title: "Tên ban đầu" });

    await vi.waitFor(() => expect(api.update).toHaveBeenCalledTimes(2), {
      timeout: 2000,
    });
    expect(api.update.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ title: "Tên ban đầu tiếp theo" }),
    );
    expect((title as HTMLInputElement).value).toBe("Tên ban đầu tiếp theo");
  });

  it("allows retrying a failed information save before moving on", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue(dossier);
    api.update
      .mockRejectedValueOnce(new Error("temporary outage"))
      .mockResolvedValue({ ...dossier, title: "Tên sau lỗi" });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    const title = await screen.findByLabelText("Tên hồ sơ");
    await user.clear(title);
    await user.type(title, "Tên sau lỗi");
    expect(
      await screen.findByRole("button", { name: "Thử lưu lại" }),
    ).toBeDefined();
    expect(
      screen.getByRole("button", { name: /Kiểm tra & nộp/ }),
    ).toHaveProperty("disabled", true);
    await user.click(screen.getByRole("button", { name: "Thử lưu lại" }));
    await vi.waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Kiểm tra & nộp/ }),
      ).toHaveProperty("disabled", false),
    );
    expect(api.update).toHaveBeenCalledTimes(2);
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
    expect(
      document.querySelector(".dossier-state-summary")?.className,
    ).toContain("bg-[var(--theme-elevated)]");
    expect(screen.getByLabelText("Tên hồ sơ").hasAttribute("disabled")).toBe(
      true,
    );
  });

  it("uses server document rules to block submission until required evidence exists", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({ ...dossier, evidences: [] });
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

    await screen.findByRole("heading", {
      level: 1,
      name: "Bộ nhận diện CNS",
    });
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));

    expect(screen.getByText("Cần bổ sung trước khi nộp")).toBeDefined();
    expect(
      screen.getByText("Chưa đáp ứng các tài liệu bắt buộc"),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Bổ sung tài liệu" }));
    expect(
      screen.getByText(/Chọn loại tài liệu, thêm tệp rồi bấm Tải lên/),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(screen.getByText("Tài liệu quyền sở hữu")).toBeDefined();
    expect(screen.getByRole("button", { name: "Nộp hồ sơ" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("uses one document chooser and keeps the category fixed while a file is queued", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({
      ...dossier,
      evidences: [],
      documentRules: [
        dossier.documentRules[0],
        {
          ...dossier.documentRules[0],
          key: "OTHER",
          label: "Tài liệu khác",
          required: false,
          maxCount: 20,
        },
      ],
    });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    const steps = await screen.findByRole("navigation", {
      name: "Các bước hoàn thiện hồ sơ",
    });
    await user.click(within(steps).getByRole("button", { name: /Bằng chứng/ }));
    expect(screen.queryByLabelText("1. Chọn loại tài liệu")).toBeNull();
    const other = screen.getByRole("button", { name: /Tài liệu khác/ });
    await user.upload(
      screen.getByLabelText("Chọn tài liệu quyền sở hữu"),
      new File(["proof"], "proof.pdf", { type: "application/pdf" }),
    );
    expect(other.hasAttribute("disabled")).toBe(true);
    await user.click(screen.getByRole("button", { name: "Xóa proof.pdf" }));
    expect(other.hasAttribute("disabled")).toBe(false);
  });
});
