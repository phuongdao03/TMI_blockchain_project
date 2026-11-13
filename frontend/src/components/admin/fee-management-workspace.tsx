"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PaymentHistoryWorkspace } from "@/components/admin/payment-history-workspace";
import { PaymentOrderReconciliation } from "@/components/admin/payment-order-reconciliation";
import { PaymentRequestWorkspace } from "@/components/admin/payment-request-workspace";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { Button } from "@/components/ui/button";
import { feeApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import type {
  AdminFeePolicy,
  AdminFeeWaiver,
  FeePolicyStatus,
  FeeWaiverStatus,
} from "@/lib/api/types";

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
  const canApplySubmissionFee =
    can("billing.fees.policies.create") && can("billing.fees.policies.approve");
  const canUseWaiverTab =
    can("billing.fees.read") || can("billing.fees.waivers.approve");
  const canListWaivers =
    can("billing.fees.read") || can("billing.fees.waivers.approve");
  const canReadTransactions = can("payments.read");
  const canIssueLegacyRequests = can("payments.issue");
  const canReconcile = can("payments.read") || can("payments.reconcile");
  const [policyAmount, setPolicyAmount] = useState("5000000");
  const [policyCancelReason, setPolicyCancelReason] = useState("");
  const [reviewPolicyId, setReviewPolicyId] = useState<string | null>(null);
  const [confirmActivation, setConfirmActivation] = useState(false);
  const [createPolicyOpen, setCreatePolicyOpen] = useState(false);
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
  const submissionPolicies = (policies.data ?? []).filter(
    (policy) => policy.feeType === "DOSSIER_SUBMISSION",
  );
  const activeSubmissionPolicy =
    submissionPolicies.find((policy) => policy.status === "ACTIVE") ?? null;
  const scheduledSubmissionPolicy =
    submissionPolicies.find((policy) => policy.status === "SCHEDULED") ?? null;
  const reviewPolicy = submissionPolicies.find(
    (policy) => policy.id === reviewPolicyId,
  );

  const refreshFees = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["admin", "fee-policies"] }),
      queryClient.invalidateQueries({ queryKey: ["admin", "fee-waivers"] }),
    ]);
    setActionError("");
  };
  const applySubmissionFee = useMutation({
    mutationFn: () =>
      feeApi.applySubmissionFee({ amountMinor: Number(policyAmount) }),
    onSuccess: async () => {
      setCreatePolicyOpen(false);
      await refreshFees();
    },
    onError: (error) => setActionError(isFeeError(error)),
  });
  const approvePolicy = useMutation({
    mutationFn: ({
      policyId,
      confirmed,
    }: {
      policyId: string;
      confirmed: boolean;
    }) => feeApi.approvePolicy(policyId, confirmed),
    onSuccess: async () => {
      setReviewPolicyId(null);
      setConfirmActivation(false);
      await refreshFees();
    },
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

  if (
    !canReadPolicies &&
    !canUseWaiverTab &&
    !canReadTransactions &&
    !canIssueLegacyRequests &&
    !canReconcile
  ) {
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
    const amount = Number(policyAmount);
    if (!Number.isSafeInteger(amount) || amount <= 0) return;
    applySubmissionFee.mutate();
  };
  const submitWaiver = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!waiverDossierId.trim() || waiverReason.trim().length < 5) return;
    grantWaiver.mutate();
  };

  return (
    <div className="workspace-screen mx-auto max-w-7xl space-y-6 pb-12">
      <WorkspacePageHeader
        description="Theo dõi mức phí chung, phiên bản chính sách và giao dịch hồ sơ."
        section="Tài chính"
        title="Quản lý phí hồ sơ"
      />

      {canReadPolicies ? (
        <section
          aria-labelledby="current-submission-fee-title"
          className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-[var(--theme-muted)]">
                Phí nộp hồ sơ hiện hành
              </p>
              <h2
                className="mt-1 text-2xl font-bold tracking-tight"
                id="current-submission-fee-title"
              >
                {activeSubmissionPolicy
                  ? money(activeSubmissionPolicy.amountMinor)
                  : "Chưa thiết lập phí nộp hồ sơ"}
              </h2>
              {activeSubmissionPolicy ? (
                <p className="mt-2 text-sm text-[var(--theme-muted)]">
                  Hiệu lực từ {formatDate(activeSubmissionPolicy.startsAt)} ·{" "}
                  {policyStatusLabels[activeSubmissionPolicy.status]} · phiên
                  bản v{activeSubmissionPolicy.versionNo}
                </p>
              ) : (
                <>
                  <p className="mt-2 max-w-2xl text-sm text-[var(--theme-muted)]">
                    Mức phí áp dụng ngay sau khi máy chủ xác nhận. Hồ sơ chưa
                    thể nộp thu phí khi chưa thiết lập giá.
                  </p>
                  {scheduledSubmissionPolicy ? (
                    <p className="mt-2 text-sm font-medium text-amber-800">
                      Đã lên lịch mức phí{" "}
                      {money(scheduledSubmissionPolicy.amountMinor)} từ{" "}
                      {formatDate(scheduledSubmissionPolicy.startsAt)}.
                    </p>
                  ) : null}
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {canApplySubmissionFee && activeSubmissionPolicy ? (
                <Button
                  onClick={() => {
                    setPolicyAmount(
                      activeSubmissionPolicy
                        ? String(activeSubmissionPolicy.amountMinor)
                        : "",
                    );
                    setActionError("");
                    setCreatePolicyOpen((open) => !open);
                  }}
                  type="button"
                >
                  Thay đổi mức phí
                </Button>
              ) : null}
              <Button
                onClick={() =>
                  document
                    .getElementById("submission-fee-history")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
                type="button"
                variant="outline"
              >
                Xem lịch sử
              </Button>
            </div>
          </div>
          {policies.isPending ? (
            <p aria-busy="true" className="text-sm text-[var(--theme-muted)]">
              Đang tải chính sách phí…
            </p>
          ) : null}
          {policies.isError ? (
            <p role="alert" className="text-sm text-red-700">
              Không tải được chính sách phí. Hãy thử tải lại trang.
            </p>
          ) : null}
        </section>
      ) : null}

      {canApplySubmissionFee &&
      (createPolicyOpen ||
        (policies.isSuccess && activeSubmissionPolicy === null)) ? (
        <form
          className="grid gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end"
          onSubmit={submitPolicy}
        >
          <div className="sm:col-span-2">
            <h2 className="text-lg font-bold">
              {activeSubmissionPolicy
                ? "Thay đổi mức phí nộp hồ sơ"
                : "Thiết lập phí nộp hồ sơ"}
            </h2>
            <p className="mt-1 text-sm text-[var(--theme-muted)]">
              Mức mới có hiệu lực ngay khi máy chủ xác nhận. Phiên bản hiện tại
              kết thúc đúng thời điểm đó; lịch đã lên vẫn được giữ.
            </p>
          </div>
          <label className="grid min-w-0 gap-1.5 text-sm font-semibold">
            Mức phí nộp hồ sơ mới (VND)
            <input
              className={fieldClass}
              inputMode="numeric"
              max="1000000000000"
              min="1"
              onChange={(event) => setPolicyAmount(event.target.value)}
              required
              type="number"
              value={policyAmount}
            />
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button disabled={applySubmissionFee.isPending} type="submit">
              {applySubmissionFee.isPending ? "Đang áp dụng…" : "Áp dụng ngay"}
            </Button>
            {activeSubmissionPolicy ? (
              <Button
                onClick={() => setCreatePolicyOpen(false)}
                type="button"
                variant="outline"
              >
                Đóng
              </Button>
            ) : null}
          </div>
          {actionError ? (
            <p className="sm:col-span-2 text-sm text-red-700" role="alert">
              {actionError}
            </p>
          ) : null}
        </form>
      ) : null}

      {reviewPolicy ? (
        <section
          aria-labelledby="policy-review-title"
          className="space-y-4 rounded-2xl border border-amber-300 bg-amber-50 p-5 text-amber-950"
        >
          <div>
            <h2 className="text-lg font-bold" id="policy-review-title">
              Xem lại trước khi kích hoạt
            </h2>
            <p className="mt-1 text-sm">
              Kiểm tra mức phí và ngày hiệu lực. Xác nhận sẽ ghi audit và kích
              hoạt hoặc lên lịch chính sách chung.
            </p>
          </div>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-semibold">Mức phí</dt>
              <dd>{money(reviewPolicy.amountMinor)}</dd>
            </div>
            <div>
              <dt className="font-semibold">Ngày hiệu lực</dt>
              <dd>{formatDate(reviewPolicy.startsAt)}</dd>
            </div>
            <div>
              <dt className="font-semibold">Lý do</dt>
              <dd>{reviewPolicy.reason}</dd>
            </div>
            <div>
              <dt className="font-semibold">Trạng thái</dt>
              <dd>{policyStatusLabels[reviewPolicy.status]}</dd>
            </div>
          </dl>
          <label className="flex items-start gap-3 text-sm font-semibold">
            <input
              checked={confirmActivation}
              className="mt-1 size-4 accent-amber-800"
              onChange={(event) => setConfirmActivation(event.target.checked)}
              type="checkbox"
            />
            Tôi xác nhận mức phí và ngày hiệu lực trên là chính xác.
          </label>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!confirmActivation || approvePolicy.isPending}
              onClick={() =>
                approvePolicy.mutate({
                  policyId: reviewPolicy.id,
                  confirmed: true,
                })
              }
              type="button"
            >
              {approvePolicy.isPending
                ? "Đang kích hoạt…"
                : "Xác nhận kích hoạt"}
            </Button>
            <Button
              onClick={() => {
                setReviewPolicyId(null);
                setConfirmActivation(false);
              }}
              type="button"
              variant="outline"
            >
              Để sau
            </Button>
          </div>
        </section>
      ) : null}

      {canReadPolicies ? (
        <section className="space-y-4" id="submission-fee-history">
          <h2 className="text-lg font-bold">Lịch sử phiên bản phí chung</h2>
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
                  <div className="min-w-0 space-y-1 text-sm">
                    <p className="font-semibold">
                      {policy.displayName} · {money(policy.amountMinor)} · v
                      {policy.versionNo}
                    </p>
                    <p className="text-[var(--theme-muted)]">
                      {policy.feeType === "DOSSIER_SUBMISSION"
                        ? "Phí nộp hồ sơ chung"
                        : policy.feeType}{" "}
                      · {policyStatusLabels[policy.status]} ·{" "}
                      {formatDate(policy.startsAt)} –{" "}
                      {formatDate(policy.endsAt)}
                    </p>
                    <p className="break-words text-[var(--theme-muted)]">
                      {policy.reason}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    {policy.status === "DRAFT" &&
                    can("billing.fees.policies.approve") ? (
                      <Button
                        onClick={() => {
                          setReviewPolicyId(policy.id);
                          setConfirmActivation(false);
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                        type="button"
                      >
                        Xem lại
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
              Chưa có phiên bản phí nào.
            </p>
          ) : policies.isPending ? (
            <p aria-busy="true">Đang tải chính sách phí…</p>
          ) : policies.isError ? (
            <p role="alert">Không tải được danh sách chính sách phí.</p>
          ) : null}
        </section>
      ) : null}

      {canUseWaiverTab ? (
        <details className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
          <summary className="cursor-pointer text-base font-bold">
            Miễn phí hồ sơ thật
          </summary>
          <section className="mt-5 space-y-5">
            {can("billing.fees.waivers.approve") ? (
              <form
                className="grid gap-4 rounded-xl border border-[var(--theme-border)] p-4 md:grid-cols-2"
                onSubmit={submitWaiver}
              >
                <h2 className="text-lg font-bold md:col-span-2">
                  Cấp miễn toàn bộ phí nộp hồ sơ
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
            {waivers.isPending ? (
              <p aria-busy="true">Đang tải yêu cầu miễn phí…</p>
            ) : null}
            {waivers.isError ? (
              <p role="alert">Không tải được danh sách miễn phí.</p>
            ) : null}
            {waivers.data?.length ? (
              <ul className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)] px-4">
                {waivers.data.map((waiver: AdminFeeWaiver) => (
                  <li
                    className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between"
                    key={waiver.id}
                  >
                    <div className="space-y-1 text-sm">
                      <p className="font-semibold">
                        {waiver.dossierId} ? {money(waiver.amountMinor)}
                      </p>
                      <p className="text-[var(--theme-muted)]">
                        {waiver.feeType} ? {waiverStatusLabels[waiver.status]} ?
                        hết hạn {formatDate(waiver.expiresAt)}
                      </p>
                      <p className="text-[var(--theme-muted)]">
                        {waiver.reason}
                      </p>
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
                          Duyệt
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
            ) : waivers.isSuccess ? (
              <p className="rounded-xl border border-[var(--theme-border)] p-4 text-sm text-[var(--theme-muted)]">
                Chưa có yêu cầu miễn phí.
              </p>
            ) : null}
          </section>
        </details>
      ) : null}

      {canReadTransactions || canIssueLegacyRequests || canReconcile ? (
        <details className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5">
          <summary className="cursor-pointer text-base font-bold">
            Giao dịch và đối soát hồ sơ legacy
          </summary>
          <div className="mt-5 space-y-6">
            <p className="rounded-xl bg-[var(--theme-elevated)] p-3 text-sm text-[var(--theme-muted)]">
              Yêu cầu thu phí thủ công chỉ dành cho hồ sơ legacy đã được duyệt;
              hồ sơ mới thanh toán phí chung trước thẩm định.
            </p>
            {canIssueLegacyRequests ? (
              <PaymentRequestWorkspace
                initialDossierId={initialDossierId}
                showReconciliation={false}
              />
            ) : null}
            {canReadTransactions ? <PaymentHistoryWorkspace /> : null}
            {canReconcile ? <PaymentOrderReconciliation /> : null}
          </div>
        </details>
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
