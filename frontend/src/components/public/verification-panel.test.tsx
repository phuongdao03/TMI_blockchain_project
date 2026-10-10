import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  it("shows a published certificate without implying a successful chain check", async () => {
    verifyToken.mockResolvedValue({
      status: "PENDING",
      networkAvailable: false,
      checkedAt: "2026-08-12T08:00:00Z",
      certificateNumber: "THV-2026-0001",
      assetTitle: "Tác phẩm công khai",
      documents: [],
    });
    certificateVersions.mockResolvedValue([]);
    renderPanel();

    expect(await screen.findByText("Chưa thể đối chiếu trực tiếp")).toBeDefined();
    expect(screen.getAllByText("THV-2026-0001").length).toBeGreaterThan(0);
    expect(screen.queryByText(/đã được xác nhận trên blockchain/)).toBeNull();
  });

  it("keeps a failed lookup retryable without claiming the certificate is invalid", async () => {
    verifyToken.mockClear();
    verifyToken
      .mockRejectedValueOnce(new Error("service unavailable"))
      .mockResolvedValueOnce({
        status: "NOT_FOUND",
        checkedAt: "2026-08-12T08:00:00Z",
      });
    renderPanel();

    expect(
      await screen.findByText("Chưa tải được kết quả tra cứu"),
    ).toBeDefined();
    expect(screen.queryByText(/Bằng xác lập đã hết hạn/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    await waitFor(() => expect(verifyToken).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Không tìm thấy bằng xác lập")).toBeDefined();
  });

  it("does not render document comparison controls on a public certificate", async () => {
    verifyToken.mockResolvedValue({
      status: "VALID",
      checkedAt: "2026-08-12T08:00:00Z",
      certificateNumber: "THV-2026-0001",
      documents: [],
    });
    certificateVersions.mockResolvedValue([]);
    renderPanel();

    await screen.findByText(/Bằng xác lập có hiệu lực/);
    expect(
      screen
        .getByAltText("Mã QR kiểm tra bằng xác lập THV-2026-0001")
        .getAttribute("src"),
    ).toMatch(/\/api\/v1\/verify\/certificate\/THV-2026-0001\/qr$/);
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
      certificateNumber: "THV-2026-0001",
      dossierCode: "ASSET-001",
      assetTitle: "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt",
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
      publicWorkSlug: "video-chao-mung-tinh-hoa-viet",
      metadataHash: "ab".repeat(32),
      blockNumber: 123,
      issuerLabel: "Đề cử Tinh Hoa Việt",
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
        issuerLabel: "Đề cử Tinh Hoa Việt",
        documents: [],
      },
    ]);

    renderPanel();

    expect(
      await screen.findByText(
        "Bằng xác lập có hiệu lực; hồ sơ đã được xác nhận trên blockchain.",
      ),
    ).toBeDefined();
    expect(await screen.findByText("Lịch sử xác nhận")).toBeDefined();
    expect(
      screen.getAllByText("Video chào mừng thương hiệu Đề cử Tinh Hoa Việt"),
    ).toHaveLength(2);
    expect(screen.getAllByText("Mạng blockchain Polygon")).toHaveLength(2);
    expect(screen.getByText("32 lượt xác nhận từ mạng")).toBeDefined();
    expect(screen.queryByText(/database|role|schema|endpoint/i)).toBeNull();
    expect(screen.getByText("Blockchain là gì?")).toBeDefined();
    expect(screen.getByText("Chi tiết nâng cao")).toBeDefined();
    expect(
      screen.getByRole("img", {
        name: "Biểu trưng Tinh Hoa Việt",
      }),
    ).toBeDefined();
    expect(
      screen.getByText("Ghi nhận tác phẩm · Tôn vinh giá trị Việt"),
    ).toBeDefined();
    expect(screen.getByText("Chủ thể hồ sơ CNS")).toBeDefined();
    const publicRecord = screen.getByRole("link", {
      name: /Xem tác phẩm/,
    });
    expect(publicRecord.getAttribute("href")).toBe(
      "/works/video-chao-mung-tinh-hoa-viet",
    );
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
