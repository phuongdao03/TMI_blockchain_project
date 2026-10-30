import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { DossierCreateForm } from "@/components/dossiers/dossier-create-form";

const api = vi.hoisted(() => ({
  create: vi.fn(),
  listTypes: vi.fn(),
  getTypeVersion: vi.fn(),
  getPreparation: vi.fn(),
  savePreparation: vi.fn(),
}));
vi.mock("@/lib/api/client", () => ({
  dossierApi: api,
  ApiError: class extends Error {},
}));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "owner-pinned" }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const oldVersion = {
  id: "old-version",
  dossierTypeId: "type-1",
  versionNo: 1,
  schema: {
    fields: [
      {
        key: "origin",
        type: "text",
        label: "Nguồn gốc đã lưu",
        required: true,
      },
    ],
  },
};
const currentType = {
  id: "type-1",
  categoryId: "category-1",
  code: "ARTWORK",
  name: "Tác phẩm nghệ thuật",
  isActive: true,
  currentVersion: {
    id: "new-version",
    dossierTypeId: "type-1",
    versionNo: 2,
    schema: {
      fields: [
        {
          key: "newRequirement",
          type: "text",
          label: "Yêu cầu phiên bản mới",
          required: true,
        },
      ],
    },
  },
};
const savedPayload = {
  dossierTypeVersionId: "old-version",
  step: 2,
  values: {
    title: "Tác phẩm đã chuẩn bị",
    summary: "Giới thiệu đã lưu",
    visibility: "PRIVATE",
  },
  formData: { origin: "Bản thảo được lưu tại tác giả" },
};

beforeEach(() => {
  sessionStorage.clear();
  Object.values(api).forEach((mock) => mock.mockReset());
  api.getPreparation.mockResolvedValue({
    ownerUserId: "owner-pinned",
    revision: 1,
    payload: savedPayload,
  });
  api.savePreparation.mockImplementation(
    async (ownerUserId, revision, payload) => ({
      ownerUserId,
      revision: revision + 1,
      payload,
    }),
  );
  api.listTypes.mockResolvedValue([currentType]);
  api.getTypeVersion.mockResolvedValue(oldVersion);
  api.create.mockResolvedValue({ id: "draft-1" });
});

function renderForm() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      <DossierCreateForm />
    </QueryClientProvider>,
  );
}

it("resumes the pinned schema after catalog publication and creates with the original values", async () => {
  const user = userEvent.setup();
  renderForm();
  const origin = await screen.findByLabelText("Nguồn gốc đã lưu *");
  expect(origin).toHaveProperty("value", savedPayload.formData.origin);
  expect(screen.queryByLabelText("Yêu cầu phiên bản mới *")).toBeNull();
  expect(api.getTypeVersion).toHaveBeenCalledWith("old-version");
  await user.click(screen.getByRole("button", { name: "Xem lại bản nháp" }));
  const create = screen.getByRole("button", { name: "Tạo hồ sơ nháp" });
  await waitFor(() => expect(create).toHaveProperty("disabled", false));
  await user.click(create);
  await waitFor(() =>
    expect(api.create.mock.calls[0]?.[0]).toEqual(
      expect.objectContaining({
        dossierTypeVersionId: "old-version",
        title: savedPayload.values.title,
        formData: savedPayload.formData,
        categoryId: "category-1",
      }),
    ),
  );
});

it("waits for the saved schema without exposing fields from the replacement version", async () => {
  let finish: (value: typeof oldVersion) => void = () => undefined;
  api.getTypeVersion.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  renderForm();
  await waitFor(() => expect(api.getTypeVersion).toHaveBeenCalled());
  expect(
    screen.getByText("Đang tải đúng phiên bản biểu mẫu đã lưu…"),
  ).toBeDefined();
  expect(screen.queryByLabelText("Yêu cầu phiên bản mới *")).toBeNull();
  expect(screen.queryByRole("button", { name: "Tạo hồ sơ nháp" })).toBeNull();
  finish(oldVersion);
  expect(await screen.findByLabelText("Nguồn gốc đã lưu *")).toHaveProperty(
    "value",
    savedPayload.formData.origin,
  );
});

it("keeps saved values when pinned-version loading fails and permits an explicit retry", async () => {
  api.getTypeVersion.mockRejectedValueOnce(new Error("Connection failed"));
  const user = userEvent.setup();
  renderForm();
  expect((await screen.findByRole("alert")).textContent).toContain(
    "biểu mẫu đã lưu",
  );
  expect(screen.queryByLabelText("Yêu cầu phiên bản mới *")).toBeNull();
  expect(api.create).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Thử tải lại biểu mẫu" }),
  );
  expect(await screen.findByLabelText("Nguồn gốc đã lưu *")).toHaveProperty(
    "value",
    savedPayload.formData.origin,
  );
});

it("does not resume or silently replace a pinned template whose type is no longer active", async () => {
  api.listTypes.mockResolvedValue([
    { ...currentType, id: "other-type", name: "Loại khác" },
  ]);
  renderForm();
  expect((await screen.findByRole("alert")).textContent).toContain(
    "biểu mẫu đã lưu",
  );
  expect(screen.queryByLabelText("Nguồn gốc đã lưu *")).toBeNull();
  expect(screen.queryByLabelText("Yêu cầu phiên bản mới *")).toBeNull();
  expect(api.create).not.toHaveBeenCalled();
  expect(api.savePreparation).not.toHaveBeenCalled();
});
