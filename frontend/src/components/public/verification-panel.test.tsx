import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VerificationPanel } from "@/components/public/verification-panel";

const verifyToken = vi.hoisted(() => vi.fn());
const certificateVersions = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  publicApi: {
    verifyToken,
    verifyNumber: vi.fn(),
    verifyTransaction: vi.fn(),
    certificateVersions,
  },
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
  it("does not render document comparison controls on a public certificate", async () => {
    verifyToken.mockResolvedValue({
      status: "VALID",
      checkedAt: "2026-08-12T08:00:00Z",
      certificateNumber: "CNS-2026-0001",
      documents: [],
    });
    certificateVersions.mockResolvedValue([]);
    renderPanel();

    await screen.findByText(/Chứng thư hợp lệ/);
    expect(
      screen
        .getByAltText("Mã QR kiểm tra chứng thư CNS-2026-0001")
        .getAttribute("src"),
    ).toMatch(/\/api\/v1\/verify\/certificate\/CNS-2026-0001\/qr$/);
    expect(screen.queryByText("Đối chiếu tài liệu")).toBeNull();
    expect(screen.queryByLabelText("Chọn tài liệu để đối chiếu")).toBeNull();
    expect(screen.queryByRole("link", { name: /Xem tác phẩm/ })).toBeNull();
  });

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
      certificateNumber: "CNS-2026-0001",
      dossierCode: "ASSET-001",
      assetTitle: "Bộ nhận diện CNS",
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
      publicWorkSlug: "bo-nhan-dien-cns",
      metadataHash: "ab".repeat(32),
      blockNumber: 123,
      issuerLabel: "Trung tâm An ninh Công nghệ số – CNS",
      recognizedSubject: "Chủ thể hồ sơ CNS",
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
        issuerLabel: "Trung tâm An ninh Công nghệ số – CNS",
        documents: [],
      },
    ]);

    renderPanel();

    expect(
      await screen.findByText(
        "Chứng thư hợp lệ và đã được xác nhận trên blockchain.",
      ),
    ).toBeDefined();
    expect(await screen.findByText("Lịch sử xác nhận")).toBeDefined();
    expect(screen.getAllByText("Bộ nhận diện CNS")).toHaveLength(2);
    expect(screen.getByText("Polygon (sổ ghi nhận công khai)")).toBeDefined();
    expect(screen.getByText("32 lượt xác nhận từ mạng")).toBeDefined();
    expect(screen.queryByText(/database|role|schema|endpoint/i)).toBeNull();
    expect(screen.getByText("Blockchain là gì?")).toBeDefined();
    expect(screen.getByText("Chi tiết nâng cao")).toBeDefined();
    expect(
      screen.getByRole("img", {
        name: "Biểu trưng Đề cử và Xác lập Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(screen.getByText("Đề cử và Xác lập Tinh Hoa Việt")).toBeDefined();
    expect(
      screen.getByText("Phát triển và vận hành công nghệ bởi CNS"),
    ).toBeDefined();
    expect(screen.queryByText("Chủ thể hồ sơ CNS")).toBeNull();
    const publicRecord = screen.getByRole("link", {
      name: /Xem tác phẩm/,
    });
    expect(publicRecord.getAttribute("href")).toBe("/works/bo-nhan-dien-cns");
    expect(publicRecord.getAttribute("target")).toBeNull();
    expect(screen.getByText("Dấu vân tay số của hồ sơ")).toBeDefined();
    expect(screen.getByText("Mã giao dịch trên blockchain")).toBeDefined();
    expect(screen.getByText("Số lượt mạng đã xác nhận")).toBeDefined();
    expect(screen.getByText("Số khối ghi nhận")).toBeDefined();
    expect(screen.getByText("Địa chỉ sổ đăng ký công khai")).toBeDefined();
    expect(
      screen.queryByText(
        /Nó không tự chứng minh tính xác thực vật lý, quyền sở hữu hoặc tính hợp pháp/,
      ),
    ).toBeNull();
  });
});
