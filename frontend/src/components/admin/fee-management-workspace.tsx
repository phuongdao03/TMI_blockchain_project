"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PaymentHistoryWorkspace } from "@/components/admin/payment-history-workspace";
import { PaymentOrderReconciliation } from "@/components/admin/payment-order-reconciliation";
import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { Button } from "@/components/ui/button";
import { dossierApi, feeApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  AdminFeePolicy,
  AdminFeeWaiver,
  FeePolicyStatus,
  FeeWaiverStatus,
} from "@/lib/api/types";

type FeeTab = "transactions" | "waivers" | "policies" | "reconciliation";

const labels: Record<FeeTab, string> = {
  transactions: "Giao dịch",
  waivers: "Miễn giảm",
  policies: "Chính sách",
  reconciliation: "Đối soát",
};

const policyStatusLabels: Record<FeePolicyStatus, string> = {
  DRAFT: "Bản nháp",
  SCHEDULED: "Đã lên lịch",
  ACTIVE: "Đang áp dụng",
  EXPIRED: "Hết hiệu lực",
  CANCELLED: "Đã hủy",
};

const waiverStatusLabels: Record<FeeWaiverStatus, string> = {
  REQUESTED: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  REDEEMED: "Đã sử dụng",
  EXPIRED: "Hết hạn",
};

const fieldClass =
  "min-h-11 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm text-[var(--theme-text)]";

function money(amount: number) {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value: string | null) {
  if (!value) return "Không giới hạn";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isFeeError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Thao tác chưa hoàn tất. Vui lòng thử lại.";
}

export function FeeManagementWorkspace({
  initialDossierId,
}: {
  initialDossierId?: string;
}) {
  const user = useAuthUser();
  const queryClient = useQueryClient();
  const permissions = user?.permissions ?? [];
  const isSuperAdmin = user?.roles.includes("SUPER_ADMIN") ?? false;
  const can = (permission: string) =>
    isSuperAdmin || permissions.includes(permission);
  const canReadPolicies =
    can("billing.fees.read") ||
    can("billing.fees.policies.create") ||
    can("billing.fees.policies.approve") ||
    can("billing.fees.policies.cancel");
  const canUseWaiverTab =
    can("billing.fees.read") || can("billing.fees.waivers.approve");
  const canListWaivers =
    can("billing.fees.read") || can("billing.fees.waivers.approve");
  const tabs: FeeTab[] = [
    ...(can("payments.read") || can("payments.issue")
      ? (["transactions"] as const)
      : []),
    ...(canUseWaiverTab ? (["waivers"] as const) : []),
    ...(canReadPolicies ? (["policies"] as const) : []),
    ...(can("payments.read") || can("payments.reconcile")
      ? (["reconciliation"] as const)
      : []),
  ];
  const [tab, setTab] = useState<FeeTab>(tabs[0] ?? "policies");
  const [policyTypeId, setPolicyTypeId] = useState("");
  const [policyAmount, setPolicyAmount] = useState("5000000");
  const [policyName, setPolicyName] = useState("");
  const [policyReason, setPolicyReason] = useState("");
  const [policyStartsAt, setPolicyStartsAt] = useState("");
  const [policyEndsAt, setPolicyEndsAt] = useState("");
  const [policyFeeType, setPolicyFeeType] = useState("DOSSIER_SUBMISSION");
  const [policyCancelReason, setPolicyCancelReason] = useState("");
  const [waiverDossierId, setWaiverDossierId] = useState(
    initialDossierId ?? "",
  );
  const [waiverReason, setWaiverReason] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [actionError, setActionError] = useState("");

  const policies = useQuery({
    queryKey: ["admin", "fee-policies"],
    queryFn: feeApi.listPolicies,
    enabled: canReadPolicies,
  });
  const waivers = useQuery({
    queryKey: ["admin", "fee-waivers"],
    queryFn: feeApi.listWaivers,
    enabled: canListWaivers,
  });
  const dossierTypes = useQuery({
    queryKey: ["dossier-types"],
    queryFn: dossierApi.listTypes,
    enabled:
      can("billing.fees.policies.create") &&
      policyFeeType !== "DOSSIER_SUBMISSION",
  });

  const refreshFees = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin", "fee-policies"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "fee-waivers"] }),
    ]);
    setActionError("");
  };
  const createPolicy = useMutation({
    mutationFn: () =>
      feeApi.createPolicy({
        feeType: policyFeeType,
        ...(policyFeeType === "DOSSIER_SUBMISSION"
          ? {}
          : { dossierTypeId: policyTypeId }),
        amountMinor: Number(policyAmount),
        startsAt: new Date(policyStartsAt).toISOString(),
        ...(policyEndsAt
          ? { endsAt: new Date(policyEndsAt).toISOString() }
          : {}),
        ...(policyName.trim() ? { displayName: policyName.trim() } : {}),
        reason: policyReason.trim(),
      }),
    onSuccess: async () => {
      setPolicyAmount("");
      setPolicyName("");
      setPolicyReason("");
      await refreshFees();
    },
    onError: (error) => setActionError(isFeeError(error)),
  });
  const approvePolicy = useMutation({
    mutationFn: feeApi.approvePolicy,
    onSuccess: refreshFees,
    onError: (error) => setActionError(isFeeError(error)),
  });
  const cancelPolicy = useMutation({
    mutationFn: ({
      policy,
      reason,
    }: {
      policy: AdminFeePolicy;
      reason: string;
    }) => feeApi.cancelPolicy(policy.id, reason),
    onSuccess: refreshFees,
    onError: (error) => setActionError(isFeeError(error)),
  });
  const grantWaiver = useMutation({
    mutationFn: () =>
      feeApi.grantSubmissionWaiver({
        dossierId: waiverDossierId.trim(),
        reason: waiverReason.trim(),
      }),
    onSuccess: async () => {
      setWaiverReason("");
      await refreshFees();
    },
    onError: (error) => setActionError(isFeeError(error)),
  });
  const decideWaiver = useMutation({
    mutationFn: ({
      waiverId,
      approve,
    }: {
      waiverId: string;
      approve: boolean;
    }) => feeApi.decideWaiver(waiverId, approve, decisionReason.trim()),
    onSuccess: refreshFees,
    onError: (error) => setActionError(isFeeError(error)),
  });

  if (tabs.length === 0) {
    return (
      <div className="workspace-screen mx-auto max-w-6xl pb-12">
        <WorkspacePageHeader
          description="Quản lý giao dịch, miễn giảm, chính sách và đối soát phí hồ sơ."
          section="Tài chính"
          title="Quản lý phí hồ sơ"
        />
        <p
          className="mt-6 rounded-xl border border-red-300 p-4 text-sm text-red-700"
          role="alert"
        >
          Tài khoản chưa được cấp quyền quản lý phí hồ sơ.
        </p>
      </div>
    );
  }

  const submitPolicy = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      (policyFeeType !== "DOSSIER_SUBMISSION" && !policyTypeId) ||
      !Number.isSafeInteger(Number(policyAmount)) ||
      Number(policyAmount) <= 0 ||
      policyReason.trim().length < 5 ||
      !policyStartsAt ||
      (policyEndsAt &&
        new Date(policyEndsAt).getTime() <= new Date(policyStartsAt).getTime())
    )
      return;
    createPolicy.mutate();
  };
  const submitWaiver = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!waiverDossierId.trim() || waiverReason.trim().length < 5) return;
    grantWaiver.mutate();
  };

  return (
    <div className="workspace-screen mx-auto max-w-7xl space-y-6 pb-12">
      <WorkspacePageHeader
        description="Quản lý giao dịch, cấp miễn phí có ghi nhận, chính sách phí theo thời hạn và đối soát."
        section="Tài chính"
        title="Quản lý phí hồ sơ"
      />
      <div
        aria-label="Phân hệ quản lý phí"
        className="flex flex-wrap gap-2"
        role="tablist"
      >
        {tabs.map((item) => (
          <button
            aria-selected={tab === item}
            className={`min-h-11 rounded-xl border px-4 text-sm font-semibold transition-colors ${tab === item ? "border-primary-700 bg-primary-700 text-white" : "border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)]"}`}
            key={item}
            onClick={() => {
              setTab(item);
              setActionError("");
            }}
            role="tab"
            type="button"
          >
            {labels[item]}
          </button>
        ))}
      </div>

      {tab === "transactions" ? (
        <div className="space-y-6" role="tabpanel">
          {can("payments.issue") ? (
            <PaymentRequestWorkspace
              initialDossierId={initialDossierId}
              showReconciliation={false}
            />
          ) : null}
          {can("payments.read") ? (
            <PaymentHistoryWorkspace />
          ) : (
            <p className="rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
              Tài khoản có thể tạo yêu cầu thu phí nhưng chưa có quyền xem lịch
              sử giao dịch.
            </p>
          )}
        </div>
      ) : null}

      {tab === "waivers" ? (
        <section className="space-y-5" role="tabpanel">
          {can("billing.fees.waivers.approve") ? (
            <form
              className="grid gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 md:grid-cols-2"
              onSubmit={submitWaiver}
            >
              <h2 className="text-lg font-bold md:col-span-2">
                Miễn toàn bộ phí nộp hồ sơ
              </h2>
              <label className="grid gap-1.5 text-sm font-semibold">
                Mã hồ sơ
                <input
                  className={fieldClass}
                  onChange={(event) => setWaiverDossierId(event.target.value)}
                  required
                  value={waiverDossierId}
                />
              </label>
              <label className="grid gap-1.5 text-sm font-semibold">
                Lý do
                <input
                  className={fieldClass}
                  maxLength={1000}
                  minLength={5}
                  onChange={(event) => setWaiverReason(event.target.value)}
                  required
                  value={waiverReason}
                />
              </label>
              <div className="flex flex-wrap items-center gap-3 md:col-span-2">
                <Button disabled={grantWaiver.isPending} type="submit">
                  Cấp miễn phí
                </Button>
                <span className="text-xs text-[var(--theme-muted)]">
                  Ghi nhận người cấp, thời điểm, mức phí gốc và lý do vào nhật
                  ký.
                </span>
              </div>
            </form>
          ) : null}
          {can("billing.fees.waivers.approve") ? (
            <label className="grid max-w-2xl gap-1.5 text-sm font-semibold">
              Lý do quyết định
              <input
                className={fieldClass}
                maxLength={1000}
                minLength={5}
                onChange={(event) => setDecisionReason(event.target.value)}
                value={decisionReason}
              />
            </label>
          ) : null}
          {!canListWaivers ? (
            <p className="rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
              Đề nghị đã gửi sẽ được người có quyền phê duyệt xem xét.
            </p>
          ) : null}
          {canListWaivers && waivers.isPending ? (
            <p aria-busy="true">Đang tải đề nghị miễn giảm…</p>
          ) : null}
          {canListWaivers && waivers.isError ? (
            <p role="alert">Không tải được danh sách đề nghị miễn giảm.</p>
          ) : null}
          {canListWaivers && waivers.data?.length ? (
            <ul className="divide-y divide-[var(--theme-border)] rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5">
              {waivers.data.map((waiver: AdminFeeWaiver) => (
                <li
                  className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
                  key={waiver.id}
                >
                  <div className="space-y-1 text-sm">
                    <p className="font-semibold">
                      {waiver.dossierId} · {money(waiver.amountMinor)}
                    </p>
                    <p className="text-[var(--theme-muted)]">
                      {waiver.feeType} · {waiverStatusLabels[waiver.status]} ·
                      hết hạn {formatDate(waiver.expiresAt)}
                    </p>
                    <p className="text-[var(--theme-muted)]">{waiver.reason}</p>
                    {waiver.status === "REQUESTED" &&
                    waiver.requestedByUserId === user?.id ? (
                      <p className="text-xs text-amber-700">
                        Người yêu cầu không thể tự phê duyệt.
                      </p>
                    ) : null}
                  </div>
                  {waiver.status === "REQUESTED" &&
                  waiver.requestedByUserId !== user?.id &&
                  can("billing.fees.waivers.approve") ? (
                    <div className="flex gap-2">
                      <Button
                        disabled={
                          decisionReason.trim().length < 5 ||
                          decideWaiver.isPending
                        }
                        onClick={() =>
                          decideWaiver.mutate({
                            waiverId: waiver.id,
                            approve: true,
                          })
                        }
                        type="button"
                      >
                        Phê duyệt
                      </Button>
                      <Button
                        disabled={
                          decisionReason.trim().length < 5 ||
                          decideWaiver.isPending
                        }
                        onClick={() =>
                          decideWaiver.mutate({
                            waiverId: waiver.id,
                            approve: false,
                          })
                        }
                        type="button"
                        variant="outline"
                      >
                        Từ chối
                      </Button>
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : canListWaivers && waivers.isSuccess ? (
            <p className="rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
              Chưa có đề nghị miễn giảm.
            </p>
          ) : null}
        </section>
      ) : null}

      {tab === "policies" ? (
        <section className="space-y-5" role="tabpanel">
          {can("billing.fees.policies.create") ? (
            <form
              className="grid gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 md:grid-cols-2 xl:grid-cols-3"
              onSubmit={submitPolicy}
            >
              <h2 className="text-lg font-bold md:col-span-2 xl:col-span-3">
                Tạo chính sách phí nháp
              </h2>
              <label className="grid gap-1.5 text-sm font-semibold">
                Loại phí
                <select
                  className={fieldClass}
                  onChange={(event) => setPolicyFeeType(event.target.value)}
                  value={policyFeeType}
                >
                  <option value="DOSSIER_SUBMISSION">Phí nộp hồ sơ</option>
                  <option value="CERTIFICATE_ISSUANCE">
                    Phí cấp chứng nhận
                  </option>
                </select>
              </label>
              {policyFeeType !== "DOSSIER_SUBMISSION" ? (
                <label className="grid gap-1.5 text-sm font-semibold">
                  Loại hồ sơ
                  <select
                    className={fieldClass}
                    onChange={(event) => setPolicyTypeId(event.target.value)}
                    required
                    value={policyTypeId}
                  >
                    <option value="">Chọn loại hồ sơ</option>
                    {dossierTypes.data
                      ?.filter((type) => type.isActive)
                      .map((type) => (
                        <option key={type.id} value={type.id}>
                          {type.name}
                        </option>
                      ))}
                  </select>
                </label>
              ) : (
                <p className="self-center text-sm text-[var(--theme-muted)]">
                  Phí áp dụng chung cho mọi loại hồ sơ.
                </p>
              )}
              <label className="grid gap-1.5 text-sm font-semibold">
                Mức phí (VND)
                <input
                  className={fieldClass}
                  min="1"
                  onChange={(event) => setPolicyAmount(event.target.value)}
                  required
                  type="number"
                  value={policyAmount}
                />
              </label>
              <label className="grid gap-1.5 text-sm font-semibold">
                Tên hiển thị
                <input
                  className={fieldClass}
                  maxLength={255}
                  onChange={(event) => setPolicyName(event.target.value)}
                  value={policyName}
                />
              </label>
              <label className="grid gap-1.5 text-sm font-semibold">
                Bắt đầu áp dụng
                <input
                  className={fieldClass}
                  onChange={(event) => setPolicyStartsAt(event.target.value)}
                  required
                  type="datetime-local"
                  value={policyStartsAt}
                />
              </label>
              <label className="grid gap-1.5 text-sm font-semibold">
                Kết thúc (tùy chọn)
                <input
                  className={fieldClass}
                  onChange={(event) => setPolicyEndsAt(event.target.value)}
                  type="datetime-local"
                  value={policyEndsAt}
                />
              </label>
              <label className="grid gap-1.5 text-sm font-semibold md:col-span-2 xl:col-span-3">
                Căn cứ / lý do
                <input
                  className={fieldClass}
                  maxLength={1000}
                  minLength={5}
                  onChange={(event) => setPolicyReason(event.target.value)}
                  required
                  value={policyReason}
                />
              </label>
              <div className="md:col-span-2 xl:col-span-3">
                <Button disabled={createPolicy.isPending} type="submit">
                  Tạo chính sách
                </Button>
                <p className="mt-2 text-xs text-[var(--theme-muted)]">
                  Chính sách chỉ có hiệu lực sau khi một quản trị viên khác phê
                  duyệt.
                </p>
              </div>
            </form>
          ) : null}
          {policies.isPending ? (
            <p aria-busy="true">Đang tải chính sách phí…</p>
          ) : null}
          {policies.isError ? (
            <p role="alert">Không tải được danh sách chính sách phí.</p>
          ) : null}
          {can("billing.fees.policies.cancel") ? (
            <label className="grid max-w-2xl gap-1.5 text-sm font-semibold">
              Lý do hủy chính sách
              <input
                className={fieldClass}
                maxLength={1000}
                minLength={5}
                onChange={(event) => setPolicyCancelReason(event.target.value)}
                value={policyCancelReason}
              />
            </label>
          ) : null}
          {policies.data?.length ? (
            <ul className="divide-y divide-[var(--theme-border)] rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-5">
              {policies.data.map((policy: AdminFeePolicy) => (
                <li
                  className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
                  key={policy.id}
                >
                  <div className="space-y-1 text-sm">
                    <p className="font-semibold">
                      {policy.displayName} · {money(policy.amountMinor)} · v
                      {policy.versionNo}
                    </p>
                    <p className="text-[var(--theme-muted)]">
                      {policy.feeType} · {policyStatusLabels[policy.status]} ·{" "}
                      {formatDate(policy.startsAt)} –{" "}
                      {formatDate(policy.endsAt)}
                    </p>
                    <p className="text-[var(--theme-muted)]">{policy.reason}</p>
                    {policy.approvedByUserId ? (
                      <p className="text-xs text-[var(--theme-muted)]">
                        Duyệt bởi {policy.approvedByUserId}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex gap-2">
                    {policy.status === "DRAFT" &&
                    policy.createdByUserId !== user?.id &&
                    can("billing.fees.policies.approve") ? (
                      <Button
                        disabled={approvePolicy.isPending}
                        onClick={() => approvePolicy.mutate(policy.id)}
                        type="button"
                      >
                        Phê duyệt
                      </Button>
                    ) : null}
                    {(policy.status === "DRAFT" ||
                      policy.status === "SCHEDULED") &&
                    can("billing.fees.policies.cancel") ? (
                      <Button
                        disabled={
                          policyCancelReason.trim().length < 5 ||
                          cancelPolicy.isPending
                        }
                        onClick={() =>
                          cancelPolicy.mutate({
                            policy,
                            reason: policyCancelReason.trim(),
                          })
                        }
                        type="button"
                        variant="outline"
                      >
                        Hủy
                      </Button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : policies.isSuccess ? (
            <p className="rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
              Chưa có chính sách phí. Mức thu mới chỉ được áp dụng sau khi tạo
              và phê duyệt chính sách.
            </p>
          ) : null}
        </section>
      ) : null}

      {tab === "reconciliation" ? (
        <div role="tabpanel">
          <PaymentOrderReconciliation />
        </div>
      ) : null}
      {actionError ? (
        <p
          className="rounded-xl border border-red-400/50 bg-red-500/5 p-3 text-sm text-red-700"
          role="alert"
        >
          {actionError}
        </p>
      ) : null}
    </div>
  );
}
