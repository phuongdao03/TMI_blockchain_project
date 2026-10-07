import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DossierCreateForm } from "@/components/dossiers/dossier-create-form";

const createMock = vi.hoisted(() => vi.fn());
const listTypesMock = vi.hoisted(() => vi.fn());
const pushMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));
vi.mock("@/lib/api/client", () => ({
  dossierApi: { create: createMock, listTypes: listTypesMock },
}));

describe("DossierCreateForm", () => {
  beforeEach(() => {
    createMock.mockReset();
    listTypesMock.mockReset();
    pushMock.mockReset();
  });

  it("uses the theme-aware active treatment for the current step", () => {
    listTypesMock.mockResolvedValue([]);
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    const activeStep = screen.getByText("Chọn loại").closest("li");
    expect(activeStep?.getAttribute("aria-current")).toBe("step");
    expect(activeStep?.className).toContain("dossier-journey__step--active");
    expect(activeStep?.className).not.toContain("bg-primary-50");
  });

  it("creates a valid draft and opens its workspace", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue({
      id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      title: "Bộ nhận diện CNS",
    });
    listTypesMock.mockResolvedValue([
      {
        id: "d1",
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
        name: "Tác phẩm văn hóa",
        code: "CULTURAL_WORK",
        isActive: true,
        currentVersion: {
          id: "v1",
          dossierTypeId: "d1",
          versionNo: 1,
          schema: {
            fields: [
              {
                key: "origin",
                type: "textarea",
                label: "Nguồn gốc tác phẩm",
                required: true,
              },
            ],
            documentRules: [
              {
                key: "source-document",
                label: "Tài liệu chứng minh nguồn gốc",
                documentType: "SOURCE_DOCUMENT",
                required: true,
                allowedMimeTypes: ["application/pdf", "image/png"],
                maxBytes: 10_485_760,
                maxCount: 3,
                defaultVisibility: "PRIVATE",
              },
            ],
          },
        },
      },
    ]);
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("radio", { name: /Tác phẩm văn hóa/ }),
    );
    expect(
      screen.getByRole("heading", { name: "Tài liệu cần chuẩn bị" }),
    ).toBeDefined();
    expect(screen.getByText("Tài liệu chứng minh nguồn gốc")).toBeDefined();
    expect(screen.getByText(/PDF, PNG/)).toBeDefined();
    expect(screen.getByText(/tối đa 10 MB · 3 tệp/)).toBeDefined();
    expect(screen.getByText(/1 trường thông tin bắt buộc/)).toBeDefined();
    expect(screen.queryByLabelText("Tên tài sản hoặc tác phẩm")).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Tiếp tục nhập thông tin" }),
    );
    await user.type(
      screen.getByLabelText("Tên tài sản hoặc tác phẩm"),
      "Bộ nhận diện CNS",
    );
    await user.type(
      screen.getByLabelText("Mô tả ngắn"),
      "Hồ sơ xác lập quyền sở hữu.",
    );
    await user.click(
      screen.getByRole("button", { name: "Tiếp tục thông tin theo loại" }),
    );
    await user.type(
      screen.getByLabelText("Nguồn gốc tác phẩm *"),
      "Tác phẩm được sáng tạo và lưu hồ sơ theo từng phiên bản.",
    );
    expect(screen.getByText("2/2 thông tin đã hoàn tất")).toBeDefined();
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra thông tin" }),
    );
    expect(
      screen.getByText("Tạo bản nháp trước khi tải tài liệu"),
    ).toBeDefined();
    expect(screen.getByText("Hồ sơ xác lập quyền sở hữu.")).toBeDefined();
    expect(
      screen.getByText(
        "Tác phẩm được sáng tạo và lưu hồ sơ theo từng phiên bản.",
      ),
    ).toBeDefined();
    expect(screen.getByText(/các mục này chưa thể chỉnh sửa/)).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Tạo hồ sơ nháp" }));

    expect(createMock.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        title: "Bộ nhận diện CNS",
        summary: "Hồ sơ xác lập quyền sở hữu.",
        visibility: "PRIVATE",
        dossierTypeVersionId: "v1",
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
      }),
    );
    expect(pushMock).toHaveBeenCalledWith(
      "/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac?created=1",
    );
  });

  it("skips type-specific information when the selected schema has no fields", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue({ id: "dossier-1" });
    listTypesMock.mockResolvedValue([
      {
        id: "d1",
        categoryId: "c1",
        name: "Hồ sơ cơ bản",
        currentVersion: {
          id: "v1",
          versionNo: 1,
          schema: { fields: [], documentRules: [] },
        },
      },
    ]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("radio", { name: /Hồ sơ cơ bản/ }),
    );
    expect(screen.queryByText("Theo loại")).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Tiếp tục nhập thông tin" }),
    );
    await user.type(
      screen.getByLabelText("Tên tài sản hoặc tác phẩm"),
      "Hồ sơ thử nghiệm",
    );
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra thông tin" }),
    );
    expect(
      screen.getByText("Tạo bản nháp trước khi tải tài liệu"),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Tạo hồ sơ nháp" }));
    expect(createMock.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        title: "Hồ sơ thử nghiệm",
        dossierTypeVersionId: "v1",
        formData: {},
      }),
    );
  });

  it("names missing required information and preserves input when moving back", async () => {
    const user = userEvent.setup();
    listTypesMock.mockResolvedValue([
      {
        id: "d1",
        categoryId: "c1",
        name: "Tác phẩm",
        currentVersion: {
          id: "v1",
          versionNo: 1,
          schema: {
            fields: [
              {
                key: "origin",
                type: "text",
                label: "Nguồn gốc",
                required: true,
              },
            ],
          },
        },
      },
    ]);
    render(
      <QueryClientProvider client={new QueryClient()}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("radio", { name: /Tác phẩm/ }));
    await user.click(
      screen.getByRole("button", { name: "Tiếp tục nhập thông tin" }),
    );
    await user.type(
      screen.getByLabelText("Tên tài sản hoặc tác phẩm"),
      "Tác phẩm mẫu",
    );
    await user.click(
      screen.getByRole("button", { name: "Tiếp tục thông tin theo loại" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra thông tin" }),
    );
    expect(screen.getByRole("alert").textContent).toContain("Nguồn gốc");
    expect(createMock).not.toHaveBeenCalled();

    await user.type(
      screen.getByLabelText("Nguồn gốc *"),
      "Lưu trữ tại tác giả",
    );
    await user.click(
      screen.getByRole("button", { name: "Kiểm tra thông tin" }),
    );
    expect(
      screen.getByText("Tạo bản nháp trước khi tải tài liệu"),
    ).toBeDefined();
    await user.click(screen.getByRole("button", { name: "Quay lại" }));
    expect(
      (screen.getByLabelText("Nguồn gốc *") as HTMLInputElement).value,
    ).toBe("Lưu trữ tại tác giả");
    await user.click(screen.getByRole("button", { name: "Quay lại" }));
    expect(
      (screen.getByLabelText("Tên tài sản hoặc tác phẩm") as HTMLInputElement)
        .value,
    ).toBe("Tác phẩm mẫu");
  });

  it("renders every type returned by the server and updates the selected context", async () => {
    const user = userEvent.setup();
    listTypesMock.mockResolvedValue([
      {
        id: "d1",
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
        name: "Tác phẩm văn hóa",
        code: "CULTURAL_WORK",
        isActive: true,
        currentVersion: {
          id: "v1",
          dossierTypeId: "d1",
          versionNo: 1,
          schema: { fields: [] },
        },
      },
      {
        id: "d2",
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
        name: "Nhãn hiệu và thương hiệu",
        code: "TRADEMARK",
        isActive: true,
        currentVersion: {
          id: "v2",
          dossierTypeId: "d2",
          versionNo: 1,
          schema: { fields: [] },
        },
      },
    ]);
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("radio", { name: /Tác phẩm văn hóa/ }),
    ).toBeTruthy();
    expect(
      screen.getByRole("radio", { name: /Nhãn hiệu và thương hiệu/ }),
    ).toBeTruthy();

    await user.click(
      screen.getByRole("radio", { name: /Nhãn hiệu và thương hiệu/ }),
    );

    expect(
      screen.getByRole("heading", { name: "Nhãn hiệu và thương hiệu" }),
    ).toBeTruthy();
  });

  it("explains a failed type request and lets the user retry", async () => {
    const user = userEvent.setup();
    listTypesMock
      .mockRejectedValueOnce(new Error("network unavailable"))
      .mockResolvedValueOnce([]);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <DossierCreateForm />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText(
        "Chưa thể tải danh mục hồ sơ. Vui lòng kiểm tra kết nối và thử lại.",
      ),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Thử tải lại" }));

    expect(listTypesMock).toHaveBeenCalledTimes(2);
  });
});
