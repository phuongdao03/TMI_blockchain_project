import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PublicWorkEditor } from "@/components/admin/public-work-editor";
import { ApiError, publicWorkAdminApi } from "@/lib/api/client";
import type { PublicWorkEditor as PublicWorkEditorData } from "@/lib/api/types";

vi.mock("@/components/media/file-uploader", () => ({
  FileUploader: () => <div data-testid="media-uploader" />,
}));

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
    publicWorkAdminApi: {
      assignTags: vi.fn(),
      attachMedia: vi.fn(),
      categories: vi.fn(),
      get: vi.fn(),
      list: vi.fn(),
      media: vi.fn(),
      preview: vi.fn(),
      publish: vi.fn(),
      removeMedia: vi.fn(),
      reorderMedia: vi.fn(),
      tags: vi.fn(),
      transition: vi.fn(),
      update: vi.fn(),
    },
  };
});

const work: PublicWorkEditorData = {
  id: "a96efbb8-fd76-4431-bc21-24caa83d0bda",
  dossierId: "25e0f889-e4af-499b-ab13-a51ba398375a",
  certificateId: "5b787209-e11d-4a41-a4ea-f4313e211c61",
  slug: "ban-mau",
  title: "Bản mẫu công khai",
  shortDescription: "Mô tả công khai đủ độ dài kiểm tra.",
  fullDescription: "Nội dung giới thiệu.",
  authorDisplayName: "TMI Studio",
  categoryId: "d822f66a-05d4-4829-85a0-4206d050480c",
  categoryName: "Nghệ thuật số",
  tagIds: [],
  thumbnailMediaId: null,
  publicationStatus: "DRAFT",
  visibility: "PUBLIC",
  publishedAt: null,
  scheduledPublishAt: null,
  featuredAt: null,
  featuredUntil: null,
  version: 2,
  checklist: [{ code: "TITLE_REQUIRED", passed: true }],
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.mocked(publicWorkAdminApi.list).mockResolvedValue({
    success: true,
    data: [work],
    meta: { page: 1, pageSize: 50, total: 1 },
  });
  vi.mocked(publicWorkAdminApi.get).mockResolvedValue(work);
  vi.mocked(publicWorkAdminApi.categories).mockResolvedValue([
    {
      id: work.categoryId,
      parentId: null,
      code: "DIGITAL_ART",
      name: work.categoryName,
      slug: "nghe-thuat-so",
      description: null,
      isActive: true,
      displayOrder: 0,
    },
  ]);
  vi.mocked(publicWorkAdminApi.tags).mockResolvedValue([]);
  vi.mocked(publicWorkAdminApi.media).mockResolvedValue([]);
  vi.mocked(publicWorkAdminApi.assignTags).mockResolvedValue(undefined);
  vi.mocked(publicWorkAdminApi.update).mockResolvedValue({ ...work, version: 3 });
  vi.mocked(publicWorkAdminApi.preview).mockResolvedValue({
    slug: work.slug,
    title: work.title,
    shortDescription: work.shortDescription,
    fullDescription: work.fullDescription,
    authorDisplayName: work.authorDisplayName,
    categoryName: work.categoryName,
    media: [],
    canPublish: true,
  });
});

afterEach(() => vi.clearAllMocks());

describe("PublicWorkEditor", () => {
  it("validates metadata and saves the server version contract", async () => {
    const user = userEvent.setup();
    render(<PublicWorkEditor />, { wrapper });

    await user.click(await screen.findByRole("button", { name: /Bản mẫu công khai/ }));
    const title = await screen.findByLabelText("Tiêu đề công khai");
    await user.clear(title);
    await user.type(title, "x");
    await user.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    expect(await screen.findByText("Tiêu đề cần ít nhất 3 ký tự.")).toBeTruthy();
    expect(publicWorkAdminApi.update).not.toHaveBeenCalled();

    await user.clear(title);
    await user.type(title, "Tác phẩm đã biên tập");
    await user.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    await waitFor(() => expect(publicWorkAdminApi.update).toHaveBeenCalled());
    expect(vi.mocked(publicWorkAdminApi.update).mock.calls[0]?.[1]).toMatchObject({
      expectedVersion: 2,
      title: "Tác phẩm đã biên tập",
    });
  });

  it("warns on unsaved changes and renders only the preview projection", async () => {
    const user = userEvent.setup();
    render(<PublicWorkEditor />, { wrapper });
    await user.click(await screen.findByRole("button", { name: /Bản mẫu công khai/ }));
    const title = await screen.findByLabelText("Tiêu đề công khai");
    await user.type(title, " mới");

    const unload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);

    await user.click(screen.getByRole("button", { name: "Xem trước" }));
    expect(await screen.findByText(work.shortDescription)).toBeTruthy();
    expect(screen.queryByText(work.dossierId)).toBeNull();
    expect(screen.getByRole("button", { name: "Xem bản mobile" })).toBeTruthy();
  });

  it("surfaces an optimistic concurrency conflict", async () => {
    vi.mocked(publicWorkAdminApi.update).mockRejectedValueOnce(
      new ApiError("Version conflict", "PUBLIC_WORK_VERSION_CONFLICT", 409),
    );
    const user = userEvent.setup();
    render(<PublicWorkEditor />, { wrapper });
    await user.click(await screen.findByRole("button", { name: /Bản mẫu công khai/ }));
    const title = await screen.findByLabelText("Tiêu đề công khai");
    await user.type(title, " mới");
    await user.click(screen.getByRole("button", { name: "Lưu thay đổi" }));
    expect(
      await screen.findByText(/Tác phẩm đã được người khác cập nhật/),
    ).toBeTruthy();
  });
});
