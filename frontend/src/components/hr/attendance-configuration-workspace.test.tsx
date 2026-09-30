import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AttendanceConfigurationWorkspace } from "@/components/hr/attendance-configuration-workspace";

const listWorksitesMock = vi.hoisted(() => vi.fn());
const createWorksiteMock = vi.hoisted(() => vi.fn());
const updateWorksiteMock = vi.hoisted(() => vi.fn());
const listPoliciesMock = vi.hoisted(() => vi.fn());
const createPolicyMock = vi.hoisted(() => vi.fn());
const correctPolicyMock = vi.hoisted(() => vi.fn());
const listAssignmentsMock = vi.hoisted(() => vi.fn());
const createAssignmentMock = vi.hoisted(() => vi.fn());
const listEmployeesMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api/client", () => ({
  ApiError: class ApiError extends Error {},
  hrAttendanceConfigurationApi: {
    listWorksites: listWorksitesMock,
    createWorksite: createWorksiteMock,
    updateWorksite: updateWorksiteMock,
    listPolicies: listPoliciesMock,
    createPolicy: createPolicyMock,
    correctPolicy: correctPolicyMock,
    listAssignments: listAssignmentsMock,
    createAssignment: createAssignmentMock,
  },
  hrEmployeeApi: { list: listEmployeesMock },
}));

const worksite = {
  id: "worksite-1",
  code: "SIN-HUB",
  name: "Singapore Hub",
  status: "ACTIVE",
  createdAt: "2026-09-21T08:00:00Z",
  updatedAt: "2026-09-21T08:00:00Z",
};

function renderWorkspace() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AttendanceConfigurationWorkspace />
    </QueryClientProvider>,
  );
}

function mockQueries() {
  listWorksitesMock.mockResolvedValue({
    success: true,
    data: [worksite],
    meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
  });
  listPoliciesMock.mockResolvedValue({
    success: true,
    data: [],
    meta: { requestId: "test", page: 1, pageSize: 100, total: 0 },
  });
  listAssignmentsMock.mockResolvedValue({
    success: true,
    data: [],
    meta: { requestId: "test", page: 1, pageSize: 100, total: 0 },
  });
  listEmployeesMock.mockResolvedValue({
    success: true,
    data: [],
    meta: { requestId: "test", page: 1, pageSize: 20, total: 0 },
  });
}

describe("AttendanceConfigurationWorkspace", () => {
  it("explains the missing employee profile and blocks assignment until a policy exists", async () => {
    mockQueries();
    renderWorkspace();

    expect(await screen.findByText("Singapore Hub")).toBeDefined();
    expect(
      (
        await screen.findByRole("link", { name: "Mở mục Nhân sự" })
      ).getAttribute("href"),
    ).toBe("/admin/employees");
    expect(
      (
        screen.getByRole("button", {
          name: "Lưu phân công",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(
      screen.getByText(/Lưu vùng chấm công trước khi phân công/),
    ).toBeDefined();
  });

  it("rejects an assignment date outside the saved policy period", async () => {
    mockQueries();
    listPoliciesMock.mockResolvedValue({
      data: [
        {
          id: "policy-1",
          worksiteId: "worksite-1",
          effectiveFrom: "2026-10-01",
          effectiveTo: null,
          timezone: "Asia/Singapore",
          latitude: "1.3521",
          longitude: "103.8198",
          radiusMeters: 180,
          maxAccuracyMeters: 35,
          createdAt: "2026-09-29T00:00:00Z",
          updatedAt: "2026-09-29T00:00:00Z",
        },
      ],
      meta: { total: 1 },
    });
    listEmployeesMock.mockResolvedValue({
      data: [
        { id: "employee-1", employeeCode: "NV001", fullName: "Nguyễn An" },
      ],
      meta: { total: 1 },
    });
    renderWorkspace();

    expect(
      await screen.findByRole("option", { name: "NV001 · Nguyễn An" }),
    ).toBeDefined();
    fireEvent.change(screen.getByLabelText("Nhân viên"), {
      target: { value: "employee-1" },
    });
    fireEvent.change(screen.getByLabelText("Ngày hiệu lực phân công"), {
      target: { value: "2026-09-30" },
    });
    fireEvent.change(screen.getByLabelText("Mã lịch làm việc"), {
      target: { value: "MON_FRI_8H" },
    });
    fireEvent.change(screen.getByLabelText("Mã lịch nghỉ lễ"), {
      target: { value: "VN-HCM" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu phân công" }));

    expect(
      screen.getByText(/Ngày phân công phải nằm trong thời gian hiệu lực/),
    ).toBeDefined();
    expect(createAssignmentMock).not.toHaveBeenCalled();
  });

  it("renames an existing worksite without replacing its historical policies", async () => {
    mockQueries();
    updateWorksiteMock.mockResolvedValue({
      ...worksite,
      name: "Văn phòng Singapore",
    });
    renderWorkspace();

    fireEvent.click(
      await screen.findByRole("button", { name: "Đổi tên Singapore Hub" }),
    );
    fireEvent.change(screen.getByLabelText("Tên địa điểm"), {
      target: { value: "Văn phòng Singapore" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu tên" }));

    await waitFor(() =>
      expect(updateWorksiteMock).toHaveBeenCalledWith("worksite-1", {
        name: "Văn phòng Singapore",
      }),
    );
  });
  it("creates a worksite from the administration workspace", async () => {
    mockQueries();
    createWorksiteMock.mockResolvedValue(worksite);
    renderWorkspace();

    expect(await screen.findByText("Chấm công theo địa điểm")).toBeDefined();
    fireEvent.click(await screen.findByRole("button", { name: "Thêm địa điểm" }));
    fireEvent.change(screen.getByLabelText("Mã điểm chấm công"), {
      target: { value: "syd-hub" },
    });
    fireEvent.change(screen.getByLabelText("Tên điểm chấm công"), {
      target: { value: "Sydney Hub" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tạo điểm chấm công" }));

    await waitFor(() => {
      expect(createWorksiteMock).toHaveBeenCalledWith({
        code: "syd-hub",
        name: "Sydney Hub",
      });
    });
  });

  it("submits an explicit per-worksite GPS policy without hidden defaults", async () => {
    mockQueries();
    createPolicyMock.mockResolvedValue({ id: "policy-1" });
    renderWorkspace();

    expect(await screen.findByText("Singapore Hub")).toBeDefined();
    fireEvent.change(screen.getByLabelText("Ngày hiệu lực"), {
      target: { value: "2026-10-01" },
    });
    fireEvent.change(screen.getByLabelText("Múi giờ IANA"), {
      target: { value: "Asia/Singapore" },
    });
    fireEvent.change(screen.getByLabelText("Vĩ độ"), {
      target: { value: "1.3521" },
    });
    fireEvent.change(screen.getByLabelText("Kinh độ"), {
      target: { value: "103.8198" },
    });
    fireEvent.change(screen.getByLabelText("Bán kính cho phép (m)"), {
      target: { value: "180" },
    });
    fireEvent.change(screen.getByLabelText("Sai số GPS tối đa (m)"), {
      target: { value: "35" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Lưu chính sách" }));

    await waitFor(() => {
      expect(createPolicyMock).toHaveBeenCalledWith("worksite-1", {
        effectiveFrom: "2026-10-01",
        effectiveTo: null,
        timezone: "Asia/Singapore",
        latitude: "1.3521",
        longitude: "103.8198",
        radiusMeters: 180,
        maxAccuracyMeters: 35,
      });
    });
  });

  it("starts a replacement policy from the current map policy without copying its effective dates", async () => {
    mockQueries();
    listPoliciesMock.mockResolvedValue({
      success: true,
      data: [
        {
          id: "policy-current",
          worksiteId: worksite.id,
          effectiveFrom: "2026-09-01",
          effectiveTo: null,
          timezone: "Asia/Singapore",
          latitude: "1.352100",
          longitude: "103.819800",
          radiusMeters: 250,
          maxAccuracyMeters: 35,
          createdAt: "2026-09-01T00:00:00Z",
          updatedAt: "2026-09-01T00:00:00Z",
        },
      ],
      meta: { requestId: "test", page: 1, pageSize: 100, total: 1 },
    });
    renderWorkspace();

    fireEvent.click(await screen.findByRole("button", { name: "Tạo phiên bản mới" }));
    expect(await screen.findByDisplayValue("Asia/Singapore")).toBeDefined();
    expect(screen.getByDisplayValue("1.352100")).toBeDefined();
    expect(screen.getByDisplayValue("103.819800")).toBeDefined();
    expect(screen.getByDisplayValue("250")).toBeDefined();
    expect(screen.getByDisplayValue("35")).toBeDefined();
    expect(
      (
        document.getElementById(
          "attendance-policy-effective-from",
        ) as HTMLInputElement
      ).value,
    ).toBe("");
    expect(
      screen.getByText(
        "Đã sao chép thông số từ chính sách gần nhất. Hãy chọn ngày hiệu lực cho phiên bản mới.",
      ),
    ).toBeDefined();
  });

  it("lets an admin correct mistaken coordinates on the current policy with a reason", async () => {
    mockQueries();
    listPoliciesMock.mockResolvedValue({ data: [{
      id: "policy-current", worksiteId: worksite.id,
      effectiveFrom: "2026-09-30", effectiveTo: null,
      timezone: "Asia/Singapore", latitude: "65.152274", longitude: "-44.236726",
      radiusMeters: 350, maxAccuracyMeters: 350,
      createdAt: "2026-09-30T00:00:00Z", updatedAt: "2026-09-30T00:00:00Z",
    }], meta: { total: 1 } });
    correctPolicyMock.mockResolvedValue({ id: "policy-current" });
    renderWorkspace();
    fireEvent.click(await screen.findByRole("button", { name: "Sửa vị trí đã lưu" }));
    fireEvent.change(screen.getByLabelText("Vĩ độ"), { target: { value: "10.717157" } });
    fireEvent.change(screen.getByLabelText("Kinh độ"), { target: { value: "106.702454" } });
    fireEvent.change(screen.getByLabelText("Lý do điều chỉnh"), { target: { value: "Chọn nhầm vị trí khi thiết lập ban đầu" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu tọa độ sửa" }));
    await waitFor(() => expect(correctPolicyMock).toHaveBeenCalledWith(
      "worksite-1", "policy-current", {
        latitude: "10.717157", longitude: "106.702454",
        radiusMeters: 350, maxAccuracyMeters: 350,
        reason: "Chọn nhầm vị trí khi thiết lập ban đầu",
      },
    ));
  });
});
