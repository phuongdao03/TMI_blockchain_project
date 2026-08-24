import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VerificationPanel } from "@/components/public/verification-panel";

const verifyToken = vi.hoisted(() => vi.fn());
const certificateVersions = vi.hoisted(() => vi.fn());
const compareLocalFile = vi.hoisted(() => vi.fn());
const verifyDocument = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  publicApi: {
    verifyToken,
    verifyNumber: vi.fn(),
    verifyTransaction: vi.fn(),
    certificateVersions,
    verifyDocument,
  },
}));
vi.mock("@/lib/verification/file-hash", () => ({
  MAX_LOCAL_VERIFICATION_BYTES: 25 * 1024 * 1024,
  compareLocalFile,
}));

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <VerificationPanel token="safe-token" />
    </QueryClientProvider>,
  );
}

describe("VerificationPanel", () => {
  it("keeps the certificate number when the form is submitted before hydration", () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <VerificationPanel />
      </QueryClientProvider>,
    );

    const form = screen
      .getByRole("button", { name: "Kiểm tra" })
      .closest("form");
    const field = screen.getByLabelText("Thông tin cần tra cứu");

    expect(form?.getAttribute("action")).toBe("/verify");
    expect(form?.getAttribute("method")).toBe("get");
    expect(field.getAttribute("name")).toBe("lookup");
  });

  it("presents a plain-language result and confirmed version history", async () => {
    verifyToken.mockResolvedValue({
      status: "VALID",
      checkedAt: "2026-08-11T08:00:00Z",
      certificateNumber: "TMI-2026-0001",
      dossierCode: "ASSET-001",
      assetTitle: "Bộ nhận diện TMI",
      categoryName: "Thiết kế",
      issuedAt: "2026-08-01T08:00:00Z",
      expiresAt: null,
      version: 2,
      network: "polygon",
      contractAddress: "0x1234",
      transactionHash: "0xabcd",
      confirmations: 32,
      confirmedAt: "2026-08-11T08:00:00Z",
      explorerUrl: "https://polygonscan.com/tx/0xabcd",
      metadataHash: "ab".repeat(32),
      blockNumber: 123,
      issuerLabel: "TMI Certificate",
      documents: [
        {
          title: "Hồ sơ công khai",
          evidenceType: "PDF",
          sha256: "cd".repeat(32),
        },
      ],
    });
    certificateVersions.mockResolvedValue([
      {
        versionNo: 2,
        status: "ACTIVE",
        metadataHash: "ab".repeat(32),
        transactionHash: "0xabcd",
        blockNumber: 123,
        confirmedAt: "2026-08-11T08:00:00Z",
        createdAt: "2026-08-10T08:00:00Z",
        issuerLabel: "TMI Certificate",
        documents: [],
      },
    ]);

    renderPanel();

    expect(
      await screen.findByText("Dữ liệu đã được ghi nhận và không thay đổi"),
    ).toBeDefined();
    expect(await screen.findByText("Lịch sử xác nhận")).toBeDefined();
    expect(screen.getByText("Bộ nhận diện TMI")).toBeDefined();
    expect(screen.queryByText(/database|role|schema|endpoint/i)).toBeNull();
  });

  it("compares a selected file locally", async () => {
    compareLocalFile.mockResolvedValue({
      status: "MATCH",
      digest: "cd".repeat(32),
    });
    renderPanel();
    const input = await screen.findByLabelText("Chọn tài liệu để đối chiếu");
    await userEvent.upload(input, new File(["proof"], "proof.pdf"));

    expect(await screen.findByText("Tài liệu trùng khớp")).toBeDefined();
    expect(compareLocalFile).toHaveBeenCalledOnce();
    expect(verifyDocument).not.toHaveBeenCalled();
  });

  it("never uploads a local file when browser hashing is unavailable", async () => {
    compareLocalFile.mockRejectedValue(
      new Error("Secure local hashing is unavailable in this browser."),
    );
    renderPanel();
    const input = await screen.findByLabelText("Chọn tài liệu để đối chiếu");
    await userEvent.upload(input, new File(["proof"], "proof.pdf"));

    expect((await screen.findByRole("alert")).textContent).toContain(
      "Trình duyệt này chưa hỗ trợ đối chiếu cục bộ",
    );
    expect(verifyDocument).not.toHaveBeenCalled();
  });

  it("does not offer a file picker when no document hash is public", async () => {
    verifyToken.mockResolvedValue({
      status: "VALID",
      checkedAt: "2026-08-12T08:00:00Z",
      certificateNumber: "TMI-2026-0001",
      documents: [],
    });
    renderPanel();

    expect(
      await screen.findByText(
        "Chứng thư này không công bố dấu vân tay tài liệu để đối chiếu công khai.",
      ),
    ).toBeDefined();
    expect(
      screen.queryByLabelText("Chọn tài liệu để đối chiếu"),
    ).toBeNull();
  });

  it("lets the user choose which public document to compare", async () => {
    verifyToken.mockResolvedValue({
      status: "VALID",
      checkedAt: "2026-08-12T08:00:00Z",
      certificateNumber: "TMI-2026-0001",
      documents: [
        { title: "Bản thứ nhất", evidenceType: "PDF", sha256: "ab".repeat(32) },
        { title: "Bản thứ hai", evidenceType: "PDF", sha256: "cd".repeat(32) },
      ],
    });
    compareLocalFile.mockResolvedValue({
      status: "MATCH",
      digest: "cd".repeat(32),
    });
    renderPanel();

    await userEvent.selectOptions(
      await screen.findByLabelText("Tài liệu cần đối chiếu"),
      "1",
    );
    await userEvent.upload(
      screen.getByLabelText("Chọn tài liệu để đối chiếu"),
      new File(["proof"], "proof.pdf"),
    );

    expect(compareLocalFile).toHaveBeenCalledWith(expect.any(File), [
      "cd".repeat(32),
    ]);
  });
});
