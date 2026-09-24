"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, ShieldCheck } from "lucide-react";
import { useState } from "react";

import { PayrollPeriodCreateForm } from "@/components/hr/payroll-period-create-form";
import { PayrollPeriodDetail } from "@/components/hr/payroll-period-detail";
import { PayrollPeriodList } from "@/components/hr/payroll-period-list";
import { HrReportDownload } from "@/components/hr/hr-report-download";
import { payrollApiMessage } from "@/components/hr/payroll-format";
import { hrAttendanceConfigurationApi, hrPayrollApi } from "@/lib/api/client";

type EntryAdjustment = {
  allowance: string;
  socialInsurance: string;
  incomeTax: string;
};

export function PayrollWorkspace() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const worksites = useQuery({
    queryKey: ["hr", "attendance-worksites", "payroll-options"],
    queryFn: () =>
      hrAttendanceConfigurationApi.listWorksites({ pageSize: 100 }),
  });
  const periods = useQuery({
    queryKey: ["hr", "payroll-periods"],
    queryFn: () => hrPayrollApi.listPeriods({ pageSize: 100 }),
    gcTime: 0,
  });
  const periodRows = periods.data?.data ?? [];
  const activePeriodId = selectedId ?? periodRows[0]?.id ?? null;
  const detail = useQuery({
    queryKey: ["hr", "payroll-period", activePeriodId],
    queryFn: () => hrPayrollApi.getPeriod(activePeriodId ?? ""),
    enabled: activePeriodId !== null,
    gcTime: 0,
  });
  const createPeriod = useMutation({ mutationFn: hrPayrollApi.createPeriod });
  const recalculate = useMutation({ mutationFn: hrPayrollApi.recalculate });
  const confirmPeriod = useMutation({ mutationFn: hrPayrollApi.confirmPeriod });
  const markPaid = useMutation({ mutationFn: hrPayrollApi.markPaid });
  const updateEntry = useMutation({
    mutationFn: ({
      payrollPeriodId,
      payrollEntryId,
      values,
    }: {
      payrollPeriodId: string;
      payrollEntryId: string;
      values: EntryAdjustment;
    }) => hrPayrollApi.updateEntry(payrollPeriodId, payrollEntryId, values),
  });

  async function refreshPayroll() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["hr", "payroll-periods"] }),
      queryClient.invalidateQueries({
        queryKey: ["hr", "payroll-period", activePeriodId],
      }),
    ]);
  }

  async function create(input: {
    worksiteId: string;
    periodMonth: string;
    standardWorkdays: number;
  }) {
    setNotice(null);
    createPeriod.reset();
    const period = await createPeriod.mutateAsync(input);
    setSelectedId(period.id);
    await refreshPayroll();
    setNotice("Đã tạo kỳ lương ở trạng thái bản nháp.");
  }

  async function calculate() {
    if (!activePeriodId) return;
    setNotice(null);
    await recalculate.mutateAsync(activePeriodId);
    await refreshPayroll();
    setNotice("Đã cập nhật số liệu kỳ lương.");
  }

  async function confirm() {
    if (!activePeriodId) return;
    setNotice(null);
    await confirmPeriod.mutateAsync(activePeriodId);
    await refreshPayroll();
    setNotice("Kỳ lương đã được xác nhận và khóa số liệu.");
  }

  async function paid() {
    if (!activePeriodId) return;
    setNotice(null);
    await markPaid.mutateAsync(activePeriodId);
    await refreshPayroll();
    setNotice("Đã ghi nhận kỳ lương đã chi.");
  }

  async function saveEntry(entryId: string, values: EntryAdjustment) {
    if (!activePeriodId) return;
    setNotice(null);
    await updateEntry.mutateAsync({
      payrollPeriodId: activePeriodId,
      payrollEntryId: entryId,
      values,
    });
    await refreshPayroll();
    setNotice("Đã lưu đầu vào và yêu cầu tính lại số liệu.");
  }

  const worksiteRows = worksites.data?.data ?? [];
  const selectedWorksiteName = worksiteRows.find(
    (item) => item.id === detail.data?.worksiteId,
  )?.name;
  const listError = periods.isError ? payrollApiMessage(periods.error) : null;
  const detailError = detail.isError ? payrollApiMessage(detail.error) : null;

  return (
    <section
      aria-labelledby="payroll-title"
      className="mx-auto max-w-7xl space-y-6 pb-12"
    >
      <header className="border-b border-neutral-200 pb-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-primary-800">
              <Banknote aria-hidden="true" className="size-4" />
              Quản trị tài chính
            </p>
            <h1
              className="mt-2 text-3xl font-bold tracking-tight text-neutral-950 sm:text-4xl"
              id="payroll-title"
            >
              Bảng lương
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
              Quản lý kỳ lương theo địa điểm làm việc, với VND, đầu vào có kiểm
              soát và trạng thái không thể đảo ngược.
            </p>
          </div>
          <p className="flex max-w-sm items-start gap-2 rounded-xl bg-neutral-100 px-3 py-2 text-sm leading-5 text-neutral-700">
            <ShieldCheck
              aria-hidden="true"
              className="mt-0.5 size-4 shrink-0 text-emerald-700"
            />
            Chỉ Super Admin được xem và thao tác dữ liệu lương.
          </p>
        </div>
      </header>
      {notice ? (
        <p
          className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900"
          role="status"
        >
          {notice}
        </p>
      ) : null}
      <PayrollPeriodCreateForm
        errorMessage={
          createPeriod.isError ? payrollApiMessage(createPeriod.error) : null
        }
        isSubmitting={createPeriod.isPending}
        onSubmit={create}
        worksites={worksiteRows}
      />
      <PayrollPeriodList
        errorMessage={listError}
        isLoading={periods.isPending}
        onRetry={() => void periods.refetch()}
        onSelect={setSelectedId}
        periods={periodRows}
        selectedId={activePeriodId}
        worksites={worksiteRows}
      />
      {activePeriodId && detail.data?.calculatedAt ? (
        <HrReportDownload
          download={() => hrPayrollApi.exportXlsx(activePeriodId)}
          errorMessage="Không thể tải báo cáo kỳ lương."
          filename="hr-payroll.xlsx"
        />
      ) : activePeriodId && detail.data && !detail.data.calculatedAt ? (
        <p className="text-sm text-amber-900" role="status">
          Tính số liệu kỳ lương trước khi xuất báo cáo Excel.
        </p>
      ) : null}
      {activePeriodId ? (
        <PayrollPeriodDetail
          errorMessage={detailError}
          isLoading={detail.isPending}
          onConfirm={confirm}
          onMarkPaid={paid}
          onRecalculate={calculate}
          onRetry={() => void detail.refetch()}
          onUpdateEntry={saveEntry}
          period={detail.data}
          worksiteName={selectedWorksiteName}
        />
      ) : null}
    </section>
  );
}
