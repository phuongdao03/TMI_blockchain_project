import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { SupplementRequestsPanel } from "@/components/supplements/supplement-requests-panel";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  respond: vi.fn(),
  decide: vi.fn(),
}));
vi.mock("@/lib/api/supplements", () => ({ supplementApi: api }));
vi.mock("@/lib/auth/user-context", () => ({
  useAuthUser: () => ({ id: "owner-1" }),
}));
const item = {
  id: "request-1",
  dossierId: "dossier-1",
  requestedVersionId: "version-1",
  criterionKey: "origin",
  criterionLabel: "Nguồn gốc",
  requestedInformation: "Bổ sung tư liệu có niên đại về quá trình sáng tác.",
  reason: "Chưa có nguồn đối chiếu độc lập cho niên đại được khai báo.",
  priority: "NORMAL",
  dueAt: null,
  createdAt: "2026-10-30T00:00:00Z",
  status: "OPEN",
  revision: 3,
  responses: [],
};
const setup = (
  props: Partial<Parameters<typeof SupplementRequestsPanel>[0]> = {},
) => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SupplementRequestsPanel
        dossierId="dossier-1"
        mode="applicant"
        canRespond
        {...props}
      />
    </QueryClientProvider>,
  );
};
beforeEach(() => {
  vi.resetAllMocks();
  api.list.mockResolvedValue([item]);
});

it("sends an owner response against the acknowledged revision and preserves history", async () => {
  const user = userEvent.setup();
  api.respond.mockImplementation(async () => {
    api.list.mockResolvedValue([{ ...item, status: "ANSWERED", revision: 4 }]);
    return { ...item, status: "ANSWERED", revision: 4 };
  });
  setup();
  expect(await screen.findByText(item.requestedInformation)).toBeDefined();
  await user.type(
    screen.getByLabelText("Nội dung xử lý yêu cầu 1"),
    "Đã bổ sung hồ sơ lưu trữ ghi nhận ngày sáng tác.",
  );
  await user.click(screen.getByRole("button", { name: "Gửi phản hồi" }));
  await waitFor(() =>
    expect(api.respond).toHaveBeenCalledWith(
      "dossier-1",
      item,
      "Đã bổ sung hồ sơ lưu trữ ghi nhận ngày sáng tác.",
    ),
  );
  expect(await screen.findByText("Đã phản hồi, chờ kiểm tra")).toBeDefined();
});

it("keeps the draft after a conflict and permits explicit discard", async () => {
  api.respond.mockRejectedValue(new Error("Conflict"));
  const user = userEvent.setup();
  setup();
  const field = await screen.findByLabelText("Nội dung xử lý yêu cầu 1");
  await user.type(
    field,
    "Thông tin giải trình vẫn phải được giữ khi lưu thất bại.",
  );
  await user.click(screen.getByRole("button", { name: "Gửi phản hồi" }));
  expect(await screen.findByText(/Chưa thể ghi nhận/)).toBeDefined();
  expect(field).toHaveProperty(
    "value",
    "Thông tin giải trình vẫn phải được giữ khi lưu thất bại.",
  );
  await user.click(
    screen.getByRole("button", { name: "Hủy nội dung đang nhập" }),
  );
  expect(field).toHaveProperty("value", "");
});

it("does not offer owner responses outside an open supplement period", async () => {
  setup({ canRespond: false });
  await screen.findByText(item.requestedInformation);
  expect(screen.queryByRole("button", { name: "Gửi phản hồi" })).toBeNull();
});

it("creates a criterion-specific request without inventing a deadline", async () => {
  const user = userEvent.setup();
  api.list.mockResolvedValue([]);
  api.create.mockResolvedValue(item);
  setup({
    mode: "reviewer",
    versionId: "version-1",
    criteria: [{ key: "origin", label: "Nguồn gốc" }],
  });
  await user.click(screen.getByText("Tạo yêu cầu bổ sung theo tiêu chí"));
  await user.selectOptions(
    screen.getByLabelText("Tiêu chí cần bổ sung"),
    "origin",
  );
  await user.type(
    screen.getByLabelText("Thông tin cần bổ sung"),
    item.requestedInformation,
  );
  await user.type(screen.getByLabelText("Lý do cần bổ sung"), item.reason);
  await user.click(screen.getByRole("button", { name: "Lưu yêu cầu bổ sung" }));
  await waitFor(() =>
    expect(api.create).toHaveBeenCalledWith("dossier-1", {
      expectedVersionId: "version-1",
      criterionKey: "origin",
      requestedInformation: item.requestedInformation,
      reason: item.reason,
      priority: "NORMAL",
      dueAt: null,
    }),
  );
});
