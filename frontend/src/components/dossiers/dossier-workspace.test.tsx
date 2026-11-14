import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DossierWorkspace } from "@/components/dossiers/dossier-workspace";
import { AuthUserProvider } from "@/lib/auth/user-context";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  update: vi.fn(),
  attachEvidence: vi.fn(),
  removeEvidence: vi.fn(),
  submit: vi.fn(),
  resubmit: vi.fn(),
  versions: vi.fn(),
  timeline: vi.fn(),
  submissionFee: vi.fn(),
  signedUrl: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  dossierApi: api,
  mediaApi: { signedUrl: api.signedUrl },
}));
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
      title: "Bằng chứng về quyền sử dụng",
      description: null,
      issuedAt: null,
      displayOrder: 0,
      isPublic: false,
      filename: "quyen-su-dung.pdf",
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
  it("shows the uploaded file name and safety-check status", async () => {
    const user = userEvent.setup();
    const openedTab = {
      opener: {} as Window | null,
      location: { href: "" },
      close: vi.fn(),
    };
    const openTab = vi
      .spyOn(window, "open")
      .mockReturnValue(openedTab as unknown as Window);
    api.signedUrl.mockResolvedValue({
      url: "https://files.example.test/doc.pdf",
    });
    api.get.mockResolvedValue(dossier);
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submissionFee.mockResolvedValue({
      feeAvailable: true,
      feeRequired: false,
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );
    await screen.findByRole("heading", { level: 1, name: dossier.title });
    await user.click(screen.getByRole("button", { name: /Tài liệu/ }));

    expect(await screen.findByText("quyen-su-dung.pdf")).toBeDefined();
    expect(screen.getByText("Đã tải lên và kiểm tra an toàn")).toBeDefined();
    expect(screen.getByLabelText("Loại tài liệu cần thêm")).toBeDefined();
    expect(screen.getByRole("button", { name: "Xem tệp" })).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Xem tệp" }));
    await vi.waitFor(() =>
      expect(api.signedUrl).toHaveBeenCalledWith(
        dossier.evidences[0]!.mediaAssetId,
      ),
    );
    expect(openedTab.location.href).toBe("https://files.example.test/doc.pdf");
    expect(openTab).toHaveBeenCalledWith("about:blank", "_blank");
  });

  it("blocks submission while fee lookup fails and preserves the draft for retry", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({ ...dossier, submissionFeeRequired: true });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submissionFee.mockRejectedValue(new Error("pricing offline"));
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );
    await screen.findByRole("heading", { level: 1, name: dossier.title });
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(
      await screen.findByText(
        "Chưa tải được phí nộp. Dữ liệu hồ sơ vẫn được giữ.",
      ),
    ).toBeDefined();
    expect(screen.getByRole("button", { name: "Nộp hồ sơ" })).toHaveProperty(
      "disabled",
      true,
    );
    api.submissionFee.mockResolvedValue({
      feeRequired: true,
      feeAvailable: true,
      amountMinor: 5_000_000,
      currency: "VND",
      policyId: "policy-1",
      policyVersionNo: 1,
      description: "Phí nộp hồ sơ",
    });
    await user.click(screen.getByRole("button", { name: "Tải lại phí nộp" }));
    expect(
      await screen.findByText(/Phí nộp hồ sơ: 5.000.000 VND/),
    ).toBeDefined();
    await user.click(screen.getByRole("checkbox"));
    expect(screen.getByRole("button", { name: "Nộp hồ sơ" })).toHaveProperty(
      "disabled",
      false,
    );
    expect(
      screen.getByRole("button", { name: "Xem / sửa tài liệu" }),
    ).toBeDefined();
  });

  it("keeps a draft unsubmitted until an active global fee policy exists", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({ ...dossier, submissionFeeRequired: true });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submissionFee.mockResolvedValue({
      feeRequired: true,
      feeAvailable: false,
      amountMinor: null,
      currency: "VND",
      policyId: null,
      policyVersionNo: null,
      description: "Chưa có chính sách phí chung đang có hiệu lực.",
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );

    await screen.findByRole("heading", { level: 1, name: dossier.title });
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(await screen.findByText(/Hồ sơ nháp vẫn được lưu/)).toBeDefined();
    expect(screen.getByRole("button", { name: "Nộp hồ sơ" })).toHaveProperty(
      "disabled",
      true,
    );
  });

  it("uses the current scoped exemption quote without a test payment mode", async () => {
    const user = userEvent.setup();
    const testDossier = { ...dossier, claims: [] };
    api.get.mockResolvedValue(testDossier);
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    api.submissionFee.mockResolvedValue({
      feeRequired: false,
      feeAvailable: true,
      amountMinor: 0,
      currency: "VND",
      description: "Phí nộp hồ sơ được miễn theo quyền kiểm thử.",
      policyId: "policy-1",
      policyVersionNo: 1,
      feeWaived: true,
      grossAmountMinor: 5_000_000,
      waiverAmountMinor: 5_000_000,
      waiverReason: "TEST_SUBMISSION_FEE_EXEMPTION",
    });
    api.submit.mockResolvedValue({
      dossier: { ...testDossier, status: "SUBMITTED", canEdit: false },
      version: { id: "version-test", submittedAt: "2026-07-31T09:00:00Z" },
    });
    render(
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <AuthUserProvider
          user={{
            id: "existing-user",
            email: "existing@example.test",
            roles: ["USER"],
            accountType: "INDIVIDUAL_APPLICANT",
            isTestAccount: false,
          }}
        >
          <DossierWorkspace dossierId={dossier.id} />
        </AuthUserProvider>
      </QueryClientProvider>,
    );

    await screen.findByRole("heading", { level: 1, name: dossier.title });
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(
      screen.getByText("Phí nộp hồ sơ được miễn theo quyền kiểm thử."),
    ).toBeDefined();
    expect(screen.getByText("Cần thanh toán")).toBeDefined();
    expect(screen.getByText("0 VND")).toBeDefined();
    expect(
      screen.queryByRole("combobox", { name: "Chế độ kiểm thử" }),
    ).toBeNull();
    await user.click(screen.getByRole("button", { name: "Nộp hồ sơ" }));

    await waitFor(() =>
      expect(api.submit).toHaveBeenCalledWith(
        dossier.id,
        expect.any(String),
        null,
        true,
      ),
    );
  });
  beforeEach(() => {
    vi.clearAllMocks();
    api.submissionFee.mockResolvedValue({
      feeRequired: false,
      feeAvailable: true,
      amountMinor: 0,
      currency: "VND",
      description: "No fee applies to this legacy fixture.",
      policyId: null,
      policyVersionNo: null,
    });
  });

  it("blocks submission when a saved claim still lacks supporting evidence", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({
      ...dossier,
      claims: [
        {
          id: "claim-1",
          criterionKey: "origin",
          statement: "Nguồn gốc còn cần bổ sung căn cứ độc lập.",
          evidenceMediaIds: [],
        },
      ],
      claimsRevision: 1,
      claimCriteria: [{ key: "origin", label: "Nguồn gốc" }],
    });
    api.versions.mockResolvedValue([]);
    api.timeline.mockResolvedValue([]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierWorkspace dossierId={dossier.id} />
      </QueryClientProvider>,
    );
    await screen.findByRole("heading", { level: 1, name: dossier.title });
    await user.click(screen.getByRole("button", { name: /Kiểm tra & nộp/ }));
    expect(screen.getByRole("alert").textContent).toContain(
      "Nhận định đã lưu còn thiếu",
    );
    expect(screen.getByRole("button", { name: "Nộp hồ sơ" })).toHaveProperty(
      "disabled",
      true,
    );
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

    expect(
      await screen.findByText(
        "Đã lưu bản nháp. Thêm tài liệu cần thiết rồi kiểm tra trước khi gửi.",
      ),
    ).toBeTruthy();
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
    expect(
      screen.getByRole("button", { name: "Xem / sửa tài liệu" }),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Nộp hồ sơ" }));
    expect(api.submit.mock.calls[0]?.[0]).toBe(dossier.id);
    expect(api.submit.mock.calls[0]?.[1]).toEqual(expect.any(String));
    expect(
      await screen.findByText("Hồ sơ đã được gửi thành công"),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", { name: "Tổng quan hồ sơ" }),
    ).toBeDefined();
    expect(
      screen.queryByRole("navigation", { name: "Các bước hoàn thiện hồ sơ" }),
    ).toBeNull();
    await user.click(screen.getByRole("button", { name: "Tài liệu đã nộp" }));
    expect(screen.getByRole("button", { name: "Xem tệp" })).toBeDefined();
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
      await screen.findByRole("heading", { name: "Tổng quan hồ sơ" }),
    ).toBeDefined();
    expect(
      screen.queryByRole("navigation", { name: "Các bước hoàn thiện hồ sơ" }),
    ).toBeNull();
    expect(screen.queryByLabelText("Tên hồ sơ")).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Tài liệu đã nộp" }),
    );
    expect(screen.getByRole("button", { name: "Xem tệp" })).toBeDefined();
    expect(screen.queryByRole("button", { name: /Xóa/ })).toBeNull();
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
    expect(screen.getByText(/Chọn loại tài liệu và tệp cần gửi/)).toBeDefined();
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
    await user.click(within(steps).getByRole("button", { name: /Tài liệu/ }));
    expect(screen.queryByLabelText("1. Chọn loại tài liệu")).toBeNull();
    const ruleSelect = screen.getByRole("combobox", {
      name: "Loại tài liệu cần thêm",
    });
    expect(ruleSelect).toHaveProperty("value", "OWNERSHIP_DOCUMENT");
    await user.selectOptions(ruleSelect, "OTHER");
    expect(ruleSelect).toHaveProperty("value", "OTHER");
    await user.upload(
      screen.getByLabelText("Chọn tệp cần thêm"),
      new File(["proof"], "proof.pdf", { type: "application/pdf" }),
    );
    expect(ruleSelect.hasAttribute("disabled")).toBe(true);
    await user.click(screen.getByRole("button", { name: "Xóa proof.pdf" }));
    expect(ruleSelect.hasAttribute("disabled")).toBe(false);
  });

  it("uses neutral document labels when the dossier type has no document rules", async () => {
    const user = userEvent.setup();
    api.get.mockResolvedValue({ ...dossier, documentRules: [], evidences: [] });
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
    await user.click(within(steps).getByRole("button", { name: /Tài liệu/ }));

    expect(
      screen.getByRole("option", {
        name: "Bằng chứng về quyền hoặc nguồn gốc",
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("option", { name: "Nội dung hoặc đối tượng đề cử" }),
    ).toBeDefined();
  });
});
