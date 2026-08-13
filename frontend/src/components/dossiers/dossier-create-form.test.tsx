import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DossierCreateForm } from "@/components/dossiers/dossier-create-form";

const createMock = vi.hoisted(() => vi.fn());
const pushMock = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));
vi.mock("@/lib/api/client", () => ({
  dossierApi: { create: createMock },
}));

describe("DossierCreateForm", () => {
  it("creates a valid draft and opens its workspace", async () => {
    const user = userEvent.setup();
    createMock.mockResolvedValue({
      id: "9155dbf5-bb3e-449d-8bf0-9572cc642cac",
      title: "Bộ nhận diện TMI",
    });
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
      }),
    );
    expect(pushMock).toHaveBeenCalledWith(
      "/dossiers/9155dbf5-bb3e-449d-8bf0-9572cc642cac",
    );
  });
});
