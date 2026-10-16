import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunityPostEditor } from "@/components/community/community-post-editor";
import type { MediaAsset, MediaPurpose } from "@/lib/api/types";

type MockUploaderProps = {
  constraints?: { allowedMimeTypes?: readonly string[]; maxBytes?: number };
  disabled?: boolean;
  label: string;
  maxFiles?: number;
  multiple?: boolean;
  onComplete: (asset: MediaAsset, index: number) => void | Promise<void>;
  purpose: MediaPurpose;
};

const api = vi.hoisted(() => ({
  categories: vi.fn(),
  createPost: vi.fn(),
  updatePost: vi.fn(),
  submitPost: vi.fn(),
  myPost: vi.fn(),
  works: vi.fn(),
}));
const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  communityApi: api,
  communityMemberApi: api,
  publicApi: { works: api.works },
}));
vi.mock("@/components/media/file-uploader", () => ({
  FileUploader: ({
    constraints,
    disabled,
    label,
    maxFiles,
    multiple,
    onComplete,
    purpose,
  }: MockUploaderProps) => (
    <section
      aria-label={label}
      data-testid="community-image-uploader"
      data-allowed-mime-types={constraints?.allowedMimeTypes?.join(",")}
      data-max-bytes={constraints?.maxBytes}
      data-max-files={maxFiles}
      data-multiple={multiple}
      data-purpose={purpose}
    >
      <button
        disabled={disabled}
        onClick={() => void onComplete(activeImage("image-1"), 0)}
        type="button"
      >
        Upload inspected image 1
      </button>
      <button
        disabled={disabled}
        onClick={() => void onComplete(activeImage("image-2"), 1)}
        type="button"
      >
        Upload inspected image 2
      </button>
    </section>
  ),
}));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.clearAllMocks();
  api.categories.mockResolvedValue([
    {
      id: "cat-1",
      name: "Di sản và văn hóa",
      slug: "heritage-culture",
      description: null,
      icon: null,
      sortOrder: 1,
    },
  ]);
  api.createPost.mockResolvedValue({
    id: "post-1",
    slug: "ky-uc-lang-co",
    title: "Ký ức làng cổ",
    content: "Nội dung ban đầu.",
    status: "DRAFT",
    images: [],
    category: {
      id: "cat-1",
      name: "Di sản và văn hóa",
      slug: "heritage-culture",
    },
    createdAt: "2026-10-13T09:00:00Z",
    updatedAt: "2026-10-13T09:00:00Z",
  });
  api.updatePost.mockResolvedValue({
    id: "post-1",
    slug: "ky-uc-lang-co",
    title: "Ký ức làng cổ",
    content: "Nội dung đã chỉnh sửa.",
    status: "DRAFT",
    images: [],
    category: {
      id: "cat-1",
      name: "Di sản và văn hóa",
      slug: "heritage-culture",
    },
    createdAt: "2026-10-13T09:00:00Z",
    updatedAt: "2026-10-13T09:10:00Z",
  });
  api.submitPost.mockResolvedValue({
    id: "post-1",
    slug: "ky-uc-lang-co",
    status: "PUBLISHED",
  });
  api.myPost.mockResolvedValue(null);
  api.works.mockResolvedValue({
    success: true,
    data: [],
    meta: { page: 1, pageSize: 6, total: 0 },
  });
});

describe("CommunityPostEditor", () => {
  it("formats and previews safely without exposing tags in the editor", async () => {
    const user = userEvent.setup();
    render(
      <CommunityPostEditor
        relatedWork={{
          id: "work-1",
          title: "Gốm làng cổ",
          slug: "gom-lang-co",
        }}
      />,
      { wrapper },
    );

    const content = await screen.findByLabelText("Nội dung");
    await user.type(content, "Hello");
    (content as HTMLTextAreaElement).setSelectionRange(0, 5);
    await user.click(screen.getByRole("button", { name: "In đậm" }));
    expect((content as HTMLTextAreaElement).value).toBe("**Hello**");

    await user.click(screen.getByRole("button", { name: "Xem trước" }));
    expect((await screen.findByText("Hello")).tagName).toBe("STRONG");
    expect(screen.getByText(/Đã liên kết:/).textContent).toContain(
      "Gốm làng cổ",
    );
    expect(screen.queryByLabelText(/Thẻ chủ đề/)).toBeNull();

    await user.type(await screen.findByLabelText("Tiêu đề"), "Câu chuyện");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(api.createPost).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Câu chuyện",
          content: "**Hello**",
          relatedWorkId: "work-1",
        }),
      ),
    );
    expect(api.createPost.mock.calls[0]?.[0]).not.toHaveProperty("tags");
  });

  it("loads and resumes an editable owned draft", async () => {
    const user = userEvent.setup();
    api.myPost.mockResolvedValue({
      id: "draft-1",
      slug: "ban-nhap",
      title: "Bản nháp",
      content: "Nội dung cũ.",
      status: "DRAFT",
      category: { id: "cat-1", name: "Di sản", slug: "di-san" },
      tags: [{ id: "tag-1", name: "làng nghề", slug: "lang-nghe" }],
      relatedWork: null,
      images: [],
      moderationReason: null,
      createdAt: "2026-10-13T09:00:00Z",
      updatedAt: "2026-10-14T09:00:00Z",
    });
    render(<CommunityPostEditor postId="draft-1" />, { wrapper });

    const title = await screen.findByLabelText("Tiêu đề");
    await waitFor(() =>
      expect((title as HTMLInputElement).value).toBe("Bản nháp"),
    );
    expect(
      (screen.getByLabelText("Nội dung") as HTMLTextAreaElement).value,
    ).toBe("Nội dung cũ.");
    expect(screen.queryByText("làng nghề")).toBeNull();
    await user.clear(title);
    await user.type(title, "Bản nháp đã sửa");
    await user.click(screen.getByRole("button", { name: "Lưu thay đổi" }));

    await waitFor(() =>
      expect(api.updatePost).toHaveBeenCalledWith(
        "draft-1",
        expect.objectContaining({
          title: "Bản nháp đã sửa",
        }),
      ),
    );
    expect(api.updatePost.mock.calls[0]?.[1]).not.toHaveProperty("tags");
  });

  it("lets the owner update a published post without sending it for review", async () => {
    const user = userEvent.setup();
    api.myPost.mockResolvedValue({
      id: "published-1",
      slug: "bai-da-dang",
      title: "Bài đã đăng",
      content: "Nội dung đã đăng.",
      status: "PUBLISHED",
      category: { id: "cat-1", name: "Di sản", slug: "di-san" },
      tags: [],
      relatedWork: null,
      images: [],
      moderationReason: null,
      createdAt: "2026-10-13T09:00:00Z",
      updatedAt: "2026-10-14T09:00:00Z",
    });
    api.updatePost.mockResolvedValue({
      id: "published-1",
      slug: "bai-da-dang",
      status: "PUBLISHED",
      images: [],
    });
    render(<CommunityPostEditor postId="published-1" />, { wrapper });

    const title = await screen.findByLabelText("Tiêu đề");
    await waitFor(() =>
      expect((title as HTMLInputElement).value).toBe("Bài đã đăng"),
    );
    await user.clear(title);
    await user.type(title, "Bài đã cập nhật");
    await user.click(screen.getByRole("button", { name: "Cập nhật bài viết" }));

    await waitFor(() =>
      expect(api.updatePost).toHaveBeenCalledWith(
        "published-1",
        expect.objectContaining({ title: "Bài đã cập nhật" }),
      ),
    );
    expect(api.submitPost).not.toHaveBeenCalled();
    expect(router.push).toHaveBeenCalledWith("/community/posts/bai-da-dang");
  });

  it("saves and edits a draft, then publishes it and opens its public page", async () => {
    const user = userEvent.setup();
    render(<CommunityPostEditor />, { wrapper });

    await user.type(await screen.findByLabelText("Tiêu đề"), "Ký ức làng cổ");
    await user.type(screen.getByLabelText("Nội dung"), "Nội dung ban đầu.");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(api.createPost).toHaveBeenCalledWith({
        title: "Ký ức làng cổ",
        content: "Nội dung ban đầu.",
        categoryId: "cat-1",
        relatedWorkId: null,
        imageMediaIds: [],
      }),
    );
    expect(await screen.findByText("Bản nháp đã được lưu.")).toBeDefined();

    const content = screen.getByLabelText("Nội dung");
    await user.clear(content);
    await user.type(content, "Nội dung đã chỉnh sửa.");
    await user.click(screen.getByRole("button", { name: "Đăng bài" }));

    await waitFor(() =>
      expect(api.updatePost).toHaveBeenCalledWith("post-1", {
        title: "Ký ức làng cổ",
        content: "Nội dung đã chỉnh sửa.",
        categoryId: "cat-1",
        relatedWorkId: null,
        imageMediaIds: [],
      }),
    );
    expect(api.submitPost).toHaveBeenCalledWith("post-1");
    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith(
        "/community/posts/ky-uc-lang-co",
      ),
    );
  });

  it("creates the draft before publishing when the user skips saving", async () => {
    const user = userEvent.setup();
    render(<CommunityPostEditor />, { wrapper });

    await user.type(await screen.findByLabelText("Tiêu đề"), "Chia sẻ mới");
    await user.type(screen.getByLabelText("Nội dung"), "Một trải nghiệm.");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(screen.getByRole("button", { name: "Đăng bài" }));

    await waitFor(() => expect(api.createPost).toHaveBeenCalledTimes(1));
    expect(api.submitPost).toHaveBeenCalledWith("post-1");
    expect(router.push).toHaveBeenCalledWith("/community/posts/ky-uc-lang-co");
  });

  it("searches public works and attaches a selected work id to a saved draft", async () => {
    const user = userEvent.setup();
    api.works.mockResolvedValueOnce({
      success: true,
      data: [
        {
          id: "public-work-1",
          title: "Nghề gốm truyền thống",
          slug: "nghe-gom-truyen-thong",
          shortDescription: "Thông tin catalog không hiển thị trong liên kết.",
          authorDisplayName: "Tác giả",
          categoryName: "Di sản",
          categorySlug: "di-san",
          tags: [],
          publishedAt: "2026-10-10T00:00:00Z",
          isFeatured: false,
          thumbnailUrl: null,
          thumbnailAltText: null,
        },
      ],
      meta: { page: 1, pageSize: 6, total: 1 },
    });
    render(<CommunityPostEditor />, { wrapper });

    await user.type(
      await screen.findByLabelText("Tiêu đề"),
      "Câu chuyện làng nghề",
    );
    await user.type(
      screen.getByLabelText("Nội dung"),
      "Một câu chuyện về nghề gốm.",
    );
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.type(screen.getByLabelText("Tìm tác phẩm đã xuất bản"), "gốm");
    await user.type(
      screen.getByLabelText("Tìm tác phẩm đã xuất bản"),
      "{Enter}",
    );

    expect(
      await screen.findByRole("button", {
        name: "Chọn tác phẩm: Nghề gốm truyền thống",
      }),
    ).toBeDefined();
    expect(api.works).toHaveBeenCalledWith({
      query: "gốm",
      page: 1,
      pageSize: 6,
      sort: "newest",
    });
    expect(api.submitPost).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", {
        name: "Chọn tác phẩm: Nghề gốm truyền thống",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(api.createPost).toHaveBeenCalledWith({
        title: "Câu chuyện làng nghề",
        content: "Một câu chuyện về nghề gốm.",
        categoryId: "cat-1",
        relatedWorkId: "public-work-1",
        imageMediaIds: [],
      }),
    );
    expect(screen.getAllByText("Nghề gốm truyền thống").length).toBe(2);
  });

  it("treats changing the selected work as an edit to an already saved draft", async () => {
    const user = userEvent.setup();
    api.works.mockResolvedValue({
      success: true,
      data: [
        { id: "public-work-2", title: "Áo dài Việt", slug: "ao-dai-viet" },
      ],
      meta: { page: 1, pageSize: 6, total: 1 },
    });
    render(<CommunityPostEditor />, { wrapper });

    await user.type(await screen.findByLabelText("Tiêu đề"), "Ký ức áo dài");
    await user.type(
      screen.getByLabelText("Nội dung"),
      "Câu chuyện về trang phục.",
    );
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));
    await waitFor(() => expect(api.createPost).toHaveBeenCalled());

    await user.type(
      screen.getByLabelText("Tìm tác phẩm đã xuất bản"),
      "áo dài",
    );
    await user.click(screen.getByRole("button", { name: "Tìm tác phẩm" }));
    await user.click(
      await screen.findByRole("button", { name: "Chọn tác phẩm: Áo dài Việt" }),
    );
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(api.updatePost).toHaveBeenCalledWith(
        "post-1",
        expect.objectContaining({
          relatedWorkId: "public-work-2",
        }),
      ),
    );
  });

  it("uploads inspected community images and previews only backend attachment DTOs", async () => {
    const user = userEvent.setup();
    api.createPost.mockImplementation(
      async (input: { imageMediaIds: string[] }) => ({
        id: "post-1",
        slug: "ky-uc-lang-co",
        title: "Ký ức làng cổ",
        content: "Nội dung.",
        status: "DRAFT",
        category: { id: "cat-1", name: "Di sản", slug: "di-san" },
        relatedWork: null,
        images: input.imageMediaIds.map((id) => ({
          id,
          url: `/api/v1/community/posts/ky-uc-lang-co/media/${id}`,
        })),
        createdAt: "2026-10-14T09:00:00Z",
        updatedAt: "2026-10-14T09:00:00Z",
      }),
    );
    api.updatePost.mockImplementation(
      async (_id: string, input: { imageMediaIds: string[] }) => ({
        id: "post-1",
        slug: "ky-uc-lang-co",
        title: "Ký ức làng cổ",
        content: "Nội dung.",
        status: "DRAFT",
        category: { id: "cat-1", name: "Di sản", slug: "di-san" },
        relatedWork: null,
        images: input.imageMediaIds.map((id) => ({
          id,
          url: `/api/v1/community/posts/ky-uc-lang-co/media/${id}`,
        })),
        createdAt: "2026-10-14T09:00:00Z",
        updatedAt: "2026-10-14T09:00:00Z",
      }),
    );
    render(<CommunityPostEditor />, { wrapper });

    const uploader = await screen.findByTestId("community-image-uploader");
    expect(uploader.getAttribute("data-purpose")).toBe("COMMUNITY_POST");
    expect(uploader.getAttribute("data-max-files")).toBe("5");
    expect(uploader.getAttribute("data-max-bytes")).toBe("5242880");
    expect(uploader.getAttribute("data-allowed-mime-types")).toBe(
      "image/jpeg,image/png,image/webp",
    );
    expect(uploader.getAttribute("data-multiple")).toBe("true");

    await user.type(await screen.findByLabelText("Tiêu đề"), "Ký ức làng cổ");
    await user.type(screen.getByLabelText("Nội dung"), "Nội dung.");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(
      screen.getByRole("button", { name: "Upload inspected image 1" }),
    );
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));

    await waitFor(() =>
      expect(api.createPost).toHaveBeenCalledWith(
        expect.objectContaining({
          imageMediaIds: ["image-1"],
        }),
      ),
    );
    const preview = await screen.findByRole("img", {
      name: "Ký ức làng cổ — ảnh đính kèm 1",
    });
    expect(preview.getAttribute("src")).toBe(
      "/api/v1/community/posts/ky-uc-lang-co/media/image-1",
    );
  });

  it("persists attachment order and removal in the ordered image ID list", async () => {
    const user = userEvent.setup();
    api.createPost.mockImplementation(
      async (input: { imageMediaIds: string[] }) => ({
        id: "post-1",
        slug: "ky-uc-lang-co",
        title: "Ký ức làng cổ",
        content: "Nội dung.",
        status: "DRAFT",
        category: { id: "cat-1", name: "Di sản", slug: "di-san" },
        relatedWork: null,
        images: input.imageMediaIds.map((id) => ({
          id,
          url: `/api/v1/community/posts/ky-uc-lang-co/media/${id}`,
        })),
        createdAt: "2026-10-14T09:00:00Z",
        updatedAt: "2026-10-14T09:00:00Z",
      }),
    );
    api.updatePost.mockImplementation(
      async (_id: string, input: { imageMediaIds: string[] }) => ({
        id: "post-1",
        slug: "ky-uc-lang-co",
        title: "Ký ức làng cổ",
        content: "Nội dung.",
        status: "DRAFT",
        category: { id: "cat-1", name: "Di sản", slug: "di-san" },
        relatedWork: null,
        images: input.imageMediaIds.map((id) => ({
          id,
          url: `/api/v1/community/posts/ky-uc-lang-co/media/${id}`,
        })),
        createdAt: "2026-10-14T09:00:00Z",
        updatedAt: "2026-10-14T09:00:00Z",
      }),
    );
    render(<CommunityPostEditor />, { wrapper });

    await user.type(await screen.findByLabelText("Tiêu đề"), "Ký ức làng cổ");
    await user.type(screen.getByLabelText("Nội dung"), "Nội dung.");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");
    await user.click(
      screen.getByRole("button", { name: "Upload inspected image 1" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Upload inspected image 2" }),
    );
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));
    await waitFor(() =>
      expect(api.createPost).toHaveBeenCalledWith(
        expect.objectContaining({
          imageMediaIds: ["image-1", "image-2"],
        }),
      ),
    );

    await user.click(
      screen.getByRole("button", { name: "Đưa ảnh 2 lên trước" }),
    );
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));
    await waitFor(() =>
      expect(api.updatePost).toHaveBeenLastCalledWith(
        "post-1",
        expect.objectContaining({
          imageMediaIds: ["image-2", "image-1"],
        }),
      ),
    );

    await user.click(screen.getByRole("button", { name: "Xóa ảnh 1" }));
    await user.click(screen.getByRole("button", { name: "Lưu bản nháp" }));
    await waitFor(() =>
      expect(api.updatePost).toHaveBeenLastCalledWith(
        "post-1",
        expect.objectContaining({
          imageMediaIds: ["image-1"],
        }),
      ),
    );
  });

  it("automatically saves a complete draft after editing pauses", async () => {
    const user = userEvent.setup();
    render(<CommunityPostEditor />, { wrapper });

    await user.type(await screen.findByLabelText("Tiêu đề"), "Auto save title");
    await user.type(screen.getByLabelText("Nội dung"), "Auto save content");
    await user.selectOptions(screen.getByLabelText("Chuyên mục"), "cat-1");

    await waitFor(
      () =>
        expect(api.createPost).toHaveBeenCalledWith(
          expect.objectContaining({
            title: "Auto save title",
            content: "Auto save content",
            categoryId: "cat-1",
          }),
        ),
      { timeout: 4_000 },
    );
    expect(await screen.findByText("Bản nháp đã tự lưu.")).toBeDefined();
  });
});

function activeImage(id: string): MediaAsset {
  return {
    id,
    status: "ACTIVE",
    mimeType: "image/png",
    bytes: 2_048,
    width: 512,
    height: 512,
    durationMs: null,
  };
}
