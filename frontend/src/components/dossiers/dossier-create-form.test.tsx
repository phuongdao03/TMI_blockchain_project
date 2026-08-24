import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
  it("creates a valid draft and opens its workspace", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue({
      id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      title: "Bộ nhận diện TMI",
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

    await user.type(
      screen.getByLabelText("Tên tài sản hoặc tác phẩm"),
      "Bộ nhận diện TMI",
    );
    await user.click(screen.getByRole("radio", { name: /Tác phẩm văn hóa/ }));
    await user.type(
      screen.getByLabelText("Mô tả ngắn"),
      "Hồ sơ xác lập quyền sở hữu.",
    );
    await user.click(screen.getByRole("button", { name: "Tạo hồ sơ nháp" }));

    expect(createMock.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        title: "Bộ nhận diện TMI",
        summary: "Hồ sơ xác lập quyền sở hữu.",
        visibility: "PRIVATE",
        dossierTypeVersionId: "v1",
        categoryId: "4d28db19-1507-5a45-a50d-cd0aa83029ec",
      }),
    );
    expect(pushMock).toHaveBeenCalledWith(
      "/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac",
    );
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
});
