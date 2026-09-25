"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe2, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { hrAttendanceConfigurationApi, hrEmployeeApi } from "@/lib/api/client";
import { AttendanceAssignmentPanel } from "./attendance-configuration-assignment-panel";
import { AttendancePolicyPanel } from "./attendance-configuration-policy-panel";
import type {
  AssignmentInput,
  PolicyInput,
  WorksiteInput,
} from "./attendance-configuration-types";
import { AttendanceWorksitePanel } from "./attendance-configuration-worksite-panel";

const pageSize = 100;

export function AttendanceConfigurationWorkspace() {
  const queryClient = useQueryClient();
  const [selectedWorksiteId, setSelectedWorksiteId] = useState<string | null>(
    null,
  );
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const worksites = useQuery({
    queryKey: ["hr", "attendance-worksites"],
    queryFn: () => hrAttendanceConfigurationApi.listWorksites({ pageSize }),
  });
  const worksiteRows = worksites.data?.data ?? [];
  const selectedWorksite =
    worksiteRows.find((item) => item.id === selectedWorksiteId) ??
    worksiteRows[0] ??
    null;
  const resolvedSelectedWorksiteId = selectedWorksite?.id ?? null;
  const policies = useQuery({
    queryKey: [
      "hr",
      "attendance-worksite-policies",
      resolvedSelectedWorksiteId,
    ],
    queryFn: () =>
      hrAttendanceConfigurationApi.listPolicies(resolvedSelectedWorksiteId!, {
        pageSize,
      }),
    enabled: Boolean(resolvedSelectedWorksiteId),
  });
  const assignments = useQuery({
    queryKey: ["hr", "attendance-assignments", resolvedSelectedWorksiteId],
    queryFn: () =>
      hrAttendanceConfigurationApi.listAssignments({
        pageSize,
        worksiteId: resolvedSelectedWorksiteId ?? undefined,
      }),
    enabled: Boolean(resolvedSelectedWorksiteId),
  });
  const employees = useQuery({
    queryKey: ["hr", "employee-candidates", employeeSearch],
    queryFn: () =>
      hrEmployeeApi.list({
        pageSize: 20,
        search: employeeSearch.trim() || undefined,
        employmentStatus: "ACTIVE",
      }),
    enabled: Boolean(resolvedSelectedWorksiteId),
  });

  const refreshWorksites = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["hr", "attendance-worksites"],
    });
  };
  const refreshPolicies = async () => {
    await queryClient.invalidateQueries({
      queryKey: [
        "hr",
        "attendance-worksite-policies",
        resolvedSelectedWorksiteId,
      ],
    });
  };
  const refreshAssignments = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["hr", "attendance-assignments", resolvedSelectedWorksiteId],
    });
  };
  const createWorksite = useMutation({
    mutationFn: (input: WorksiteInput) =>
      hrAttendanceConfigurationApi.createWorksite(input),
    onSuccess: async (worksite) => {
      setSelectedWorksiteId(worksite.id);
      setNotice(
        "Đã tạo địa điểm làm việc. Hãy thiết lập vùng chấm công trước khi phân công.",
      );
      await refreshWorksites();
    },
  });
  const updateWorksite = useMutation({
    mutationFn: ({ id, changes }: { id: string; changes: { name?: string; status?: "ACTIVE" | "INACTIVE" } }) =>
      hrAttendanceConfigurationApi.updateWorksite(id, changes),
    onSuccess: async () => {
      setNotice("Đã cập nhật trạng thái địa điểm làm việc.");
      await refreshWorksites();
    },
  });
  const createPolicy = useMutation({
    mutationFn: ({
      worksiteId,
      input,
    }: {
      worksiteId: string;
      input: PolicyInput;
    }) => hrAttendanceConfigurationApi.createPolicy(worksiteId, input),
    onSuccess: async () => {
      setNotice("Đã lưu chính sách vùng chấm công theo thời điểm hiệu lực.");
      await refreshPolicies();
    },
  });
  const createAssignment = useMutation({
    mutationFn: (input: AssignmentInput) =>
      hrAttendanceConfigurationApi.createAssignment(input),
    onSuccess: async () => {
      setNotice("Đã phân công địa điểm làm việc cho nhân viên.");
      await refreshAssignments();
    },
  });

  return (
    <section
      aria-labelledby="attendance-configuration-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="relative overflow-hidden rounded-3xl border border-neutral-800 bg-neutral-950 px-5 py-7 text-white shadow-sm sm:px-8 sm:py-9">
        <div className="absolute -right-10 -top-12 size-48 rounded-full bg-primary-500/15 blur-3xl" />
        <div className="relative max-w-3xl">
          <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-primary-200">
            <Globe2 aria-hidden="true" className="size-4" />
            Điều hành nhân sự toàn cầu
          </span>
          <h1
            className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl"
            id="attendance-configuration-title"
          >
            Địa điểm làm việc toàn cầu
          </h1>
          <p className="mt-3 text-sm leading-6 text-neutral-300 sm:text-base">
            Thiết lập từng địa điểm, vùng chấm công và lịch làm việc theo múi
            giờ thực tế — không dùng một quy tắc chung cho mọi quốc gia.
          </p>
        </div>
      </header>

      <aside className="flex gap-3 rounded-2xl border border-primary-100 bg-primary-50/70 p-4 text-sm leading-6 text-primary-950">
        <ShieldCheck
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-primary-700"
        />
        <p>
          Tọa độ chỉ được dùng khi nhân viên chủ động chấm công vào hoặc ra.
          Chính sách và phân công được lưu theo lịch sử; không sửa lại bằng cách
          ghi đè dữ liệu cũ.
        </p>
      </aside>

      {notice ? (
        <p
          aria-live="polite"
          className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800"
        >
          {notice}
        </p>
      ) : null}

      <AttendanceWorksitePanel
        isCreating={createWorksite.isPending}
        isUpdating={updateWorksite.isPending}
        onCreate={(input) => createWorksite.mutateAsync(input)}
        onSelect={setSelectedWorksiteId}
        onToggleActive={(worksite) =>
          updateWorksite.mutateAsync({
            id: worksite.id,
            changes: { status: worksite.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" },
          })
        }
        onRename={(worksite, name) => updateWorksite.mutateAsync({ id: worksite.id, changes: { name } })}
        onRetry={() => void worksites.refetch()}
        selectedWorksiteId={resolvedSelectedWorksiteId}
        worksites={worksites}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <AttendancePolicyPanel
          isSaving={createPolicy.isPending}
          key={resolvedSelectedWorksiteId ?? "no-worksite"}
          onRetry={() => void policies.refetch()}
          onSave={(input) =>
            createPolicy.mutateAsync({
              worksiteId: resolvedSelectedWorksiteId!,
              input,
            })
          }
          policies={policies}
          selectedWorksite={selectedWorksite}
        />
        <AttendanceAssignmentPanel
          assignments={assignments}
          employeeSearch={employeeSearch}
          employees={employees}
          isSaving={createAssignment.isPending}
          onEmployeeSearch={setEmployeeSearch}
          onRetry={() => void assignments.refetch()}
          onSave={(input) => createAssignment.mutateAsync(input)}
          selectedWorksite={selectedWorksite}
        />
      </div>
    </section>
  );
}
