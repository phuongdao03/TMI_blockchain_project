import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TaskWorkspace } from "@/components/tasks/task-workspace";

const listTasksMock = vi.hoisted(() => vi.fn());
const createTaskMock = vi.hoisted(() => vi.fn());
const updateTaskMock = vi.hoisted(() => vi.fn());
const exportTasksMock = vi.hoisted(() => vi.fn());
const saveWorkbookMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/download", () => ({ saveWorkbook: saveWorkbookMock }));

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  taskAdminApi: {
    list: listTasksMock,
    create: createTaskMock,
    update: updateTaskMock,
    exportXlsx: exportTasksMock,
  },
}));

describe("TaskWorkspace", () => {
  it("creates a task and starts a pending task after confirmation", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    listTasksMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "task-1",
          title: "Prepare release notes",
          description: null,
          status: "TODO",
          priority: "MEDIUM",
          assigneeEmployeeId: null,
          createdByUserId: "user-1",
          dueAt: null,
          completedAt: null,
          createdAt: "2026-09-20T01:00:00Z",
          updatedAt: "2026-09-20T01:00:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    createTaskMock.mockResolvedValue({ id: "task-2" });
    updateTaskMock.mockResolvedValue({ id: "task-1" });
    exportTasksMock.mockResolvedValue(new Blob(["xlsx"]));
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <TaskWorkspace />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Prepare release notes")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Xuất Excel" }));
    await waitFor(() => {
      expect(exportTasksMock).toHaveBeenCalledWith({
        search: undefined,
        status: undefined,
        priority: undefined,
      });
      expect(saveWorkbookMock).toHaveBeenCalledWith(
        expect.any(Blob),
        "hr-tasks.xlsx",
      );
    });
    fireEvent.change(screen.getByLabelText("Tên công việc"), {
      target: { value: "Publish release notes" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tạo công việc" }));
    await waitFor(() => {
      expect(createTaskMock).toHaveBeenCalledWith({
        title: "Publish release notes",
        description: null,
        dueAt: null,
      });
    });
    fireEvent.click(screen.getByRole("button", { name: "Bắt đầu" }));
    await waitFor(() => {
      expect(updateTaskMock).toHaveBeenCalledWith("task-1", {
        status: "IN_PROGRESS",
      });
    });
  });

  it("shows a clear error when a status transition is rejected", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    listTasksMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "task-1",
          title: "Prepare release notes",
          description: null,
          status: "TODO",
          priority: "MEDIUM",
          assigneeEmployeeId: null,
          createdByUserId: "user-1",
          dueAt: null,
          completedAt: null,
          createdAt: "2026-09-20T01:00:00Z",
          updatedAt: "2026-09-20T01:00:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 20, total: 1 },
    });
    updateTaskMock.mockRejectedValue(new Error("Conflict"));
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <TaskWorkspace />
      </QueryClientProvider>,
    );

    await screen.findByText("Prepare release notes");
    fireEvent.click(screen.getByRole("button", { name: "Bắt đầu" }));

    expect(
      await screen.findByText(
        "Không thể cập nhật công việc. Vui lòng thử lại.",
      ),
    ).toBeDefined();
  });
});
