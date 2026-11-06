"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";
import { adminWithdrawalApi, withdrawalApi } from "@/lib/api/client";
import type { WalletWithdrawalStatus } from "@/lib/api/types";
import { useAuthUser } from "@/lib/auth/user-context";
import {
  payoutAttemptStatusLabel,
  withdrawalStatusLabel,
} from "@/lib/wallet-presentation";
import { formatVnd } from "@/lib/wallet/summary";

import { FinanceControlsPanel } from "./finance-controls-panel";
import { WithdrawalVerificationPanel } from "./withdrawal-verification-panel";

const inputClass =
  "min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-sm";

export function AdminWithdrawalsWorkspace() {
  const user = useAuthUser();
  const client = useQueryClient();
  const [status, setStatus] =
    useState<WalletWithdrawalStatus>("PENDING_REVIEW");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [actionNotice, setActionNotice] = useState("");
  const [actionError, setActionError] = useState(false);
  const [confirmPayout, setConfirmPayout] = useState(false);
  const roles = user?.roles ?? [];
  const permissions = user?.permissions ?? [];
  const canRead =
    roles.includes("SUPER_ADMIN") || permissions.includes("finance.read");
  const canApprove =
    roles.includes("SUPER_ADMIN") ||
    permissions.includes("finance.withdrawals.approve");
  const canExecutePayout =
    roles.includes("SUPER_ADMIN") ||
    permissions.includes("finance.payouts.execute");
  const canVerifyIdentity =
    roles.includes("SUPER_ADMIN") ||
    permissions.includes("finance.identity.verify");
  const canManageSettings =
    roles.includes("SUPER_ADMIN") ||
    permissions.includes("finance.settings.manage");
  const canManageBanks =
    roles.includes("SUPER_ADMIN") ||
    permissions.includes("finance.banks.manage");
  const list = useQuery({
    queryKey: ["admin", "withdrawals", status],
    queryFn: () => adminWithdrawalApi.list(status),
    enabled: canRead,
  });
  const withdrawalSettings = useQuery({
    queryKey: ["admin", "withdrawal-settings"],
    queryFn: withdrawalApi.settings,
    enabled: canRead,
  });
  const detail = useQuery({
    queryKey: ["admin", "withdrawals", selectedId],
    queryFn: () => adminWithdrawalApi.detail(selectedId!),
    enabled: canRead && Boolean(selectedId),
  });
  const refresh = async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ["admin", "withdrawals"] }),
      selectedId
        ? client.invalidateQueries({
            queryKey: ["admin", "withdrawals", selectedId],
          })
        : Promise.resolve(),
    ]);
  };
  const approve = useMutation({
    mutationFn: adminWithdrawalApi.approve,
    onSuccess: async (result) => {
      setActionError(false);
      setActionNotice(
        result.status === "APPROVED"
          ? "Đã duyệt. Yêu cầu vẫn chờ bước xử lý chi trả theo quy trình tài chính."
          : "Đã ghi nhận lượt duyệt. Yêu cầu cần thêm phê duyệt theo hạn mức.",
      );
      await refresh();
    },
    onError: () => {
      setActionNotice("");
      setActionError(true);
    },
  });
  const dispatchPayout = useMutation({
    mutationFn: adminWithdrawalApi.dispatchPayout,
    onSuccess: async () => {
      setActionError(false);
      setActionNotice(
        "Đã gửi lệnh chi trả. Theo dõi trạng thái yêu cầu tại đây.",
      );
      setConfirmPayout(false);
      await refresh();
    },
    onError: () => {
      setActionNotice("");
      setActionError(true);
    },
  });
  const reject = useMutation({
    mutationFn: () => adminWithdrawalApi.reject(selectedId!, reason.trim()),
    onSuccess: async () => {
      setActionError(false);
      setActionNotice("Đã từ chối yêu cầu rút.");
      setReason("");
      await refresh();
    },
    onError: () => {
      setActionNotice("");
      setActionError(true);
    },
  });

  return (
    <main className="workspace-screen mx-auto max-w-6xl space-y-6 pb-12">
      <WorkspacePageHeader
        description="Kiểm tra thông tin và ghi nhận phê duyệt theo quyền tài chính."
        icon={Wallet}
        section="Tài chính"
        title="Yêu cầu rút tiền"
      />
      {!canRead ? (
        <p
          role="alert"
          className="rounded-xl border border-red-300 p-4 text-sm text-red-700"
        >
          Bạn không có quyền xem yêu cầu rút tiền.
        </p>
      ) : (
        <>
          <section
            aria-label="Bộ lọc và danh sách yêu cầu rút"
            className="space-y-5 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
          >
            <p className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
              Phê duyệt ghi nhận quyết định quản trị; thao tác này không tự động
              chuyển tiền.
            </p>
            <p className="text-sm text-[var(--theme-muted)]">
              Trạng thái chi trả tự động:{" "}
              <span className="font-semibold text-[var(--theme-foreground)]">
                {withdrawalSettings.isPending
                  ? "đang kiểm tra"
                  : withdrawalSettings.isError
                    ? "chưa xác định"
                    : withdrawalSettings.data?.payoutLiveEnabled
                      ? "đang bật"
                      : "đang tắt"}
              </span>
            </p>
            <label className="grid max-w-xs gap-1 text-sm font-semibold">
              Lọc theo trạng thái
              <select
                className={inputClass}
                onChange={(event) =>
                  setStatus(event.target.value as WalletWithdrawalStatus)
                }
                value={status}
              >
                {[
                  ["PENDING_REVIEW", "Chờ xét duyệt"],
                  ["APPROVED", "Đã duyệt"],
                  ["REJECTED", "Đã từ chối"],
                  ["CANCELLED", "Đã hủy"],
                  ["QUEUED", "Đang chờ chi trả"],
                  ["PROCESSING", "Đang xử lý"],
                  ["RECONCILIATION_REQUIRED", "Cần kiểm tra giao dịch"],
                  ["SUCCEEDED", "Đã hoàn tất"],
                  ["FAILED", "Không thành công"],
                ].map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            {list.isPending ? (
              <p
                aria-busy="true"
                className="py-8 text-center text-sm"
                role="status"
              >
                Đang tải yêu cầu rút…
              </p>
            ) : list.isError ? (
              <div
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
                role="alert"
              >
                <p className="text-sm text-red-700">
                  Chưa tải được yêu cầu rút.
                </p>
                <Button
                  className="min-h-10"
                  onClick={() => void list.refetch()}
                  type="button"
                  variant="outline"
                >
                  Tải lại
                </Button>
              </div>
            ) : list.data?.length ? (
              <ul className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)] px-4">
                {list.data.map((item) => (
                  <li className="py-4" key={item.id}>
                    <article className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                      <div className="min-w-0 space-y-1">
                        <p className="text-xs text-[var(--theme-muted)]">
                          Mã yêu cầu{" "}
                          <span className="font-mono font-semibold text-[var(--theme-foreground)]">
                            {item.providerReference}
                          </span>
                        </p>
                        <p className="font-semibold">
                          {item.bankNameSnapshot} · {item.accountNumberMasked}
                        </p>
                        <p className="text-sm text-[var(--theme-muted)]">
                          {formatVnd(item.amountMinor)} · Phí{" "}
                          {formatVnd(item.feeMinor)} · Thực nhận{" "}
                          {formatVnd(item.netAmountMinor)}
                        </p>
                        <p className="text-xs text-[var(--theme-muted)]">
                          {new Date(item.createdAt).toLocaleString("vi-VN")}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-3 py-2 text-xs font-bold">
                          {withdrawalStatusLabel(item.status)}
                        </span>
                        <Button
                          aria-label={`Xem chi tiết yêu cầu ${item.providerReference}`}
                          className="min-h-11"
                          onClick={() => {
                            setSelectedId(item.id);
                            setActionNotice("");
                            setActionError(false);
                            setReason("");
                            setConfirmPayout(false);
                          }}
                          type="button"
                          variant="outline"
                        >
                          Xem chi tiết
                        </Button>
                      </div>
                    </article>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="rounded-xl border border-dashed border-[var(--theme-border)] p-8 text-center text-sm text-[var(--theme-muted)]">
                Không có yêu cầu ở trạng thái này.
              </p>
            )}
          </section>

          {selectedId ? (
            <section
              aria-labelledby="withdrawal-detail-title"
              className="space-y-4 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 id="withdrawal-detail-title" className="text-xl font-bold">
                  Chi tiết yêu cầu
                </h2>
                <Button
                  className="min-h-10"
                  onClick={() => setSelectedId(null)}
                  type="button"
                  variant="outline"
                >
                  Đóng
                </Button>
              </div>
              {detail.isPending ? (
                <p aria-busy="true" className="text-sm" role="status">
                  Đang tải chi tiết…
                </p>
              ) : detail.isError || !detail.data ? (
                <div
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-300 p-4"
                  role="alert"
                >
                  <p className="text-sm text-red-700">
                    Chưa tải được chi tiết yêu cầu.
                  </p>
                  <Button
                    className="min-h-10"
                    onClick={() => void detail.refetch()}
                    type="button"
                    variant="outline"
                  >
                    Tải lại
                  </Button>
                </div>
              ) : (
                <>
                  <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Mã người dùng
                      </dt>
                      <dd className="mt-1 break-all font-mono">
                        {detail.data.userId}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--theme-muted)]">Ngân hàng</dt>
                      <dd className="mt-1 font-semibold">
                        {detail.data.bankNameSnapshot} ·{" "}
                        {detail.data.bankBinSnapshot}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Chủ tài khoản
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {detail.data.accountName}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Số tài khoản
                      </dt>
                      <dd className="mt-1 font-mono font-semibold">
                        {detail.data.accountNumber}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--theme-muted)]">
                        Số tiền yêu cầu
                      </dt>
                      <dd className="mt-1 font-semibold">
                        {formatVnd(detail.data.amountMinor)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[var(--theme-muted)]">Trạng thái</dt>
                      <dd className="mt-1 font-semibold">
                        {withdrawalStatusLabel(detail.data.status)}
                      </dd>
                    </div>
                  </dl>
                  <p className="text-sm text-[var(--theme-muted)]">
                    Đã ghi nhận {detail.data.approvals.length} lượt phê duyệt.
                    {detail.data.status === "PENDING_REVIEW"
                      ? " Hạn mức có thể yêu cầu phê duyệt từ nhiều người."
                      : ""}
                  </p>
                  {canVerifyIdentity ? (
                    <WithdrawalVerificationPanel
                      onComplete={() => void refresh()}
                      userId={detail.data.userId}
                      withdrawalId={detail.data.id}
                    />
                  ) : null}
                  {detail.data.payoutAttempts.length ? (
                    <section
                      aria-labelledby="payout-attempts-title"
                      className="border-t border-[var(--theme-border)] pt-4"
                    >
                      <h3 id="payout-attempts-title" className="font-bold">
                        Lịch sử chi trả
                      </h3>
                      <ul className="mt-2 divide-y divide-[var(--theme-border)]">
                        {detail.data.payoutAttempts.map((attempt) => (
                          <li
                            className="flex flex-wrap justify-between gap-2 py-2 text-sm"
                            key={attempt.id}
                          >
                            <span className="font-mono">
                              {attempt.referenceId}
                            </span>
                            <span>
                              {payoutAttemptStatusLabel(attempt.status)} ·{" "}
                              {attempt.attemptCount} lần thử
                            </span>
                            {attempt.providerErrorCode ? (
                              <span className="text-red-700">
                                Mã lỗi: {attempt.providerErrorCode}
                              </span>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </section>
                  ) : null}
                  {canApprove && detail.data.status === "PENDING_REVIEW" ? (
                    <div className="grid gap-3 border-t border-[var(--theme-border)] pt-4 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-end">
                      <label className="grid gap-1 text-sm font-semibold sm:col-span-3">
                        Lý do từ chối (bắt buộc khi từ chối)
                        <textarea
                          className="min-h-24 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-3 text-sm"
                          maxLength={1000}
                          minLength={10}
                          onChange={(event) => setReason(event.target.value)}
                          value={reason}
                        />
                      </label>
                      {detail.data.userId === user?.id ? (
                        <p className="text-sm text-red-700 sm:col-span-3">
                          Người tạo yêu cầu không được tự phê duyệt yêu cầu này.
                        </p>
                      ) : null}
                      <Button
                        className="min-h-11"
                        disabled={
                          approve.isPending || detail.data.userId === user?.id
                        }
                        onClick={() => approve.mutate(selectedId)}
                        type="button"
                      >
                        {approve.isPending
                          ? "Đang ghi nhận…"
                          : "Ghi nhận phê duyệt"}
                      </Button>
                      <Button
                        className="min-h-11"
                        disabled={reason.trim().length < 10 || reject.isPending}
                        onClick={() => reject.mutate()}
                        type="button"
                        variant="outline"
                      >
                        {reject.isPending ? "Đang từ chối…" : "Từ chối yêu cầu"}
                      </Button>
                    </div>
                  ) : null}
                  {canExecutePayout && detail.data.status === "APPROVED" ? (
                    <div className="space-y-3 border-t border-red-300 pt-4">
                      <div>
                        <h3 className="font-bold text-red-900">
                          Gửi lệnh chi trả
                        </h3>
                        <p className="mt-1 text-sm text-[var(--theme-muted)]">
                          Đây là bước riêng sau khi phê duyệt. Khi cấu hình và
                          thông tin payOS hợp lệ, lệnh này có thể chuyển tiền
                          thật.
                        </p>
                      </div>
                      <label className="flex items-start gap-2 text-sm font-semibold">
                        <input
                          checked={confirmPayout}
                          onChange={(event) =>
                            setConfirmPayout(event.target.checked)
                          }
                          type="checkbox"
                        />
                        Tôi đã đối chiếu người nhận và số tiền, xác nhận gửi
                        lệnh chi trả.
                      </label>
                      <Button
                        className="min-h-11"
                        disabled={
                          !withdrawalSettings.data?.payoutLiveEnabled ||
                          !confirmPayout ||
                          dispatchPayout.isPending
                        }
                        onClick={() => dispatchPayout.mutate(selectedId)}
                        type="button"
                      >
                        {dispatchPayout.isPending
                          ? "Đang gửi lệnh…"
                          : "Gửi lệnh chi trả"}
                      </Button>
                      {!withdrawalSettings.data?.payoutLiveEnabled ? (
                        <p role="status" className="text-sm text-amber-900">
                          Chi trả tự động đang tắt hoặc chưa xác định. Chỉ bật
                          trong cấu hình sau khi hoàn tất kiểm tra vận hành.
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                  {actionNotice ? (
                    <p
                      role="status"
                      className="text-sm font-semibold text-emerald-800"
                    >
                      {actionNotice}
                    </p>
                  ) : null}
                  {actionError ? (
                    <p role="alert" className="text-sm text-red-700">
                      Chưa nhận được kết quả chi trả. Hãy kiểm tra trạng thái
                      yêu cầu trước khi thử lại.
                    </p>
                  ) : null}
                </>
              )}
            </section>
          ) : null}
          <FinanceControlsPanel
            canManageBanks={canManageBanks}
            canManageSettings={canManageSettings}
            canRead={canRead}
            settings={withdrawalSettings.data}
            settingsError={withdrawalSettings.isError}
            settingsLoading={withdrawalSettings.isPending}
            onRetrySettings={() => void withdrawalSettings.refetch()}
          />
        </>
      )}
    </main>
  );
}
