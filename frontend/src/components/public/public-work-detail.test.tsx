import {
  focusManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublicWorkDetailPage } from "@/components/public/public-work-detail";
import {
  PUBLIC_WORK_ACTION_EVENT,
  type PublicWorkActionEvent,
} from "@/lib/analytics/public-work-actions";
import { ApiError, publicApi } from "@/lib/api/client";
import type { PublicWorkDetail } from "@/lib/api/types";

vi.mock("@/lib/api/client", () => {
  class TestApiError extends Error {
    constructor(
      message: string,
      readonly code: string,
      readonly status: number,
    ) {
      super(message);
    }
  }
  return {
    ApiError: TestApiError,
    publicApi: {
      recordShare: vi.fn(),
      recordView: vi.fn(),
      reportWork: vi.fn(),
      verifyNumber: vi.fn(),
      work: vi.fn(),
    },
  };
});

const detail: PublicWorkDetail = {
  id: "03f15dce-f57b-4ec8-9960-1fefbd4ff307",
  slug: "di-san-so",
  title: "Di sản số TMI",
  shortDescription: "Mô tả công khai đã được duyệt.",
  fullDescription: "Nội dung dài\nđược giữ đúng định dạng văn bản.",
  authorDisplayName: "TMI Studio",
  organizationDisplayName: "TMI Group",
  categoryName: "Nghệ thuật số",
  categorySlug: "nghe-thuat-so",
  tags: [{ name: "Đương đại", slug: "duong-dai" }],
  publishedAt: "2026-07-31T10:00:00Z",
  visibility: "PUBLIC",
  certificate: {
    certificateNumber: "TMI-2026-0001",
    status: "ACTIVE",
    issuedAt: "2026-07-31T09:00:00Z",
    expiresAt: null,
  },
  proof: {
    network: "local",
    transactionHash: `0x${"12".repeat(32)}`,
    status: "CONFIRMED",
    confirmations: 4,
    confirmedAt: "2026-07-31T10:02:00Z",
  },
  media: [],
  relatedWorks: [],
  canonicalSlug: "di-san-so",
  redirected: false,
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(publicApi.recordShare).mockResolvedValue({ accepted: true });
  vi.mocked(publicApi.recordView).mockResolvedValue(undefined);
  vi.mocked(publicApi.work).mockResolvedValue(detail);
  vi.mocked(publicApi.verifyNumber).mockResolvedValue({
    status: "PENDING",
    checkedAt: "2026-07-31T10:03:00Z",
    certificateNumber: detail.certificate!.certificateNumber,
    assetTitle: detail.title,
    categoryName: detail.categoryName,
    issuedAt: detail.certificate!.issuedAt,
    expiresAt: null,
    version: 1,
    network: "local",
    contractAddress: null,
    transactionHash: detail.proof!.transactionHash,
    confirmations: 4,
    confirmedAt: detail.proof!.confirmedAt,
    explorerUrl: null,
  });
  vi.mocked(publicApi.reportWork).mockResolvedValue({
    id: "2855298e-5b1a-4e50-b9fd-277aca988b34",
    status: "OPEN",
  });
});

afterEach(() => {
  focusManager.setFocused(undefined);
  vi.clearAllMocks();
});

describe("PublicWorkDetailPage", () => {
  it("records a non-blocking view when the public work becomes visible", async () => {
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(publicApi.recordView).toHaveBeenCalledWith(detail.canonicalSlug);
    });
  });

  it("renders a deliberate no-media state", async () => {
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    expect(screen.getByRole("heading", { name: detail.title })).toBeTruthy();
    expect(screen.getByText("Hình ảnh đang được cập nhật")).toBeTruthy();
  });

  it("distinguishes published proof from temporarily unavailable verification", async () => {
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    expect(await screen.findByText("Chưa thể đối chiếu lúc này")).toBeTruthy();
    expect(screen.getByText(detail.proof!.transactionHash!)).toBeTruthy();
    expect(screen.getByText("Trạng thái xác nhận")).toBeTruthy();
  });

  it("renders long untrusted-looking content as plain text", () => {
    const unsafeLooking = {
      ...detail,
      fullDescription: `Mở đầu\n${"Nội dung an toàn. ".repeat(80)}<script>alert(1)</script>`,
    };
    const { container } = render(
      <PublicWorkDetailPage initialDetail={unsafeLooking} slug={detail.slug} />,
      { wrapper },
    );
    expect(screen.getByText(/<script>alert\(1\)<\/script>/)).toBeTruthy();
    expect(container.querySelector("script")).toBeNull();
  });

  it("replaces stale content when the work becomes suspended", async () => {
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    await waitFor(() => expect(publicApi.work).toHaveBeenCalled());
    vi.mocked(publicApi.work).mockRejectedValue(
      new ApiError("Not found", "PUBLIC_WORK_NOT_FOUND", 404),
    );
    focusManager.setFocused(false);
    focusManager.setFocused(true);
    expect(
      await screen.findByText("Tác phẩm không còn công khai"),
    ).toBeTruthy();
    expect(
      screen
        .getByRole("status", { name: "Tác phẩm không còn công khai" })
        .classList.contains("public-status-panel"),
    ).toBe(true);
    expect(
      screen
        .getByRole("link", { name: "Trở lại danh sách đề cử" })
        .classList.contains("public-status-panel__action"),
    ).toBe(true);
  });

  it("emits typed QR/report hook events", async () => {
    const events: PublicWorkActionEvent[] = [];
    const listener = (event: Event) =>
      events.push((event as CustomEvent<PublicWorkActionEvent>).detail);
    window.addEventListener(PUBLIC_WORK_ACTION_EVENT, listener);
    const user = userEvent.setup();
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    await user.click(screen.getByRole("button", { name: "QR" }));
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Báo cáo" }));
    expect(events.map((event) => event.action)).toEqual([
      "qr_requested",
      "report_requested",
    ]);
    window.removeEventListener(PUBLIC_WORK_ACTION_EVENT, listener);
  });

  it("submits an accessible public content report", async () => {
    const user = userEvent.setup();
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    await user.click(screen.getByRole("button", { name: "Báo cáo" }));
    expect(
      screen.getByRole("dialog", { name: "Báo cáo nội dung" }),
    ).toBeTruthy();
    await user.selectOptions(
      screen.getByLabelText(/Lý do/),
      "INCORRECT_INFORMATION",
    );
    await user.type(
      screen.getByLabelText("Mô tả bổ sung"),
      "Thông tin cần được kiểm tra.",
    );
    await user.type(
      screen.getByLabelText(/Email liên hệ/),
      "reporter@example.test",
    );
    await user.click(screen.getByRole("button", { name: "Gửi báo cáo" }));
    await waitFor(() =>
      expect(publicApi.reportWork).toHaveBeenCalledWith(detail.id, {
        reason: "INCORRECT_INFORMATION",
        description: "Thông tin cần được kiểm tra.",
        reporterEmail: "reporter@example.test",
      }),
    );
    expect(await screen.findByText("Đã tiếp nhận báo cáo")).toBeTruthy();
  });

  it("copies only the canonical work URL", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    window.history.replaceState({}, "", "/works/old-slug?tracking=secret");
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    await user.click(screen.getByRole("button", { name: "Sao chép liên kết" }));
    expect(writeText).toHaveBeenCalledWith(
      "http://localhost:3000/works/di-san-so",
    );
    expect(
      await screen.findByText("Đã sao chép liên kết chính thức."),
    ).toBeTruthy();
  });

  it("opens an accessible downloadable QR dialog", async () => {
    const user = userEvent.setup();
    render(<PublicWorkDetailPage initialDetail={detail} slug={detail.slug} />, {
      wrapper,
    });
    await user.click(screen.getByRole("button", { name: "QR" }));
    const dialog = screen.getByRole("dialog", { name: "Quét để mở tác phẩm" });
    expect(dialog).toBeTruthy();
    expect(screen.getByRole("button", { name: "Đóng mã QR" })).toBe(
      document.activeElement,
    );
    expect(
      screen
        .getByRole("img", { name: /Mã QR mở tác phẩm/ })
        .getAttribute("src"),
    ).toContain("/api/v1/public/works/di-san-so/qr");
    expect(
      screen.getByRole("link", { name: "Tải mã QR" }).getAttribute("href"),
    ).toBe("/api/v1/public/works/di-san-so/qr");
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
