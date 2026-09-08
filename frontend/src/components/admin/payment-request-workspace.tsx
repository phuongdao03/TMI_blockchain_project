"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeDollarSign,
  CheckCircle2,
  Clock3,
  Gift,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { paymentApi } from "@/lib/api/client";

type FeeMode = "PAID" | "FREE";

let fallbackRequestSequence = 0;

function requestKey() {
  fallbackRequestSequence += 1;
  return (
    globalThis.crypto?.randomUUID?.() ??
    `payment-decision-${Date.now()}-${fallbackRequestSequence}`
  );
}

const controlClass =
  "min-h-12 w-full rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-[var(--theme-text)] outline-none transition-[border-color,box-shadow] focus:border-primary-500 focus:ring-4 focus:ring-primary-500/10";

export function PaymentRequestWorkspace() {
  const queryClient = useQueryClient();
  const [dossierId, setDossierId] = useState("");
  const [mode, setMode] = useState<FeeMode>("PAID");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState(
    "Phí xác lập và phát hành chứng thư",
  );
  const [dueAt, setDueAt] = useState("");
  const [waiverReason, setWaiverReason] = useState("");
  const idempotencyKey = useRef(requestKey());
  const candidates = useQuery({
    queryKey: ["admin", "payment-candidates"],
    queryFn: paymentApi.listCandidates,
  });
  const selected = useMemo(
    () => candidates.data?.find((item) => item.dossierId === dossierId),
    [candidates.data, dossierId],
  );
  const refreshCandidates = () =>
    queryClient.invalidateQueries({
      queryKey: ["admin", "payment-candidates"],
    });
  const finishDecision = () => {
    idempotencyKey.current = requestKey();
    void refreshCandidates();
  };
  const issue = useMutation({
    mutationFn: () =>
      paymentApi.issue(
        dossierId,
        {
          amountMinor: Number(amount),
          currency: "VND",
          description: description.trim(),
          ...(dueAt ? { dueAt: new Date(dueAt).toISOString() } : {}),
        },
        idempotencyKey.current,
      ),
    onSuccess: finishDecision,
  });
  const waive = useMutation({
    mutationFn: () =>
      paymentApi.waive(dossierId, waiverReason.trim(), idempotencyKey.current),
    onSuccess: finishDecision,
  });
  const pending = issue.isPending || waive.isPending;
  const paidValid =
    Number.isInteger(Number(amount)) &&
    Number(amount) >= 1_000 &&
    Number(amount) <= 1_000_000_000 &&
    description.trim().length >= 5;
  const valid =
    Boolean(dossierId) &&
    (mode === "PAID" ? paidValid : waiverReason.trim().length >= 5);
  const success = mode === "PAID" ? issue.data : waive.data;
  const error = mode === "PAID" ? issue.error : waive.error;

  const changeDossier = (nextDossierId: string) => {
    setDossierId(nextDossierId);
    idempotencyKey.current = requestKey();
    issue.reset();
    waive.reset();
  };

  const changeMode = (nextMode: FeeMode) => {
    setMode(nextMode);
    idempotencyKey.current = requestKey();
    issue.reset();
    waive.reset();
  };

  return (
    <main className="payment-request-workspace mx-auto max-w-6xl space-y-6 pb-12">
      <header className="overflow-hidden rounded-3xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
        <div className="grid gap-6 p-6 sm:p-9 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <p className="font-mono text-xs font-bold uppercase tracking-[0.2em] text-primary-700">
              Sau phê duyệt · trước blockchain
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-5xl">
              Quyết định phí hồ sơ
            </h1>
            <p className="mt-4 max-w-2xl leading-7 text-[var(--theme-muted)]">
              Chọn hồ sơ đã phê duyệt, gửi yêu cầu thanh toán hoặc xác nhận miễn
              phí. Chỉ hồ sơ đã hoàn tất bước này mới xuất hiện trong hàng đợi
              ký.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] px-4 py-3 text-sm">
            <ShieldCheck
              className="size-5 text-emerald-600"
              aria-hidden="true"
            />
            <span>
              <strong>Kiểm soát 2 bước</strong>
              <br />
              Phí → ký blockchain
            </span>
          </div>
        </div>
        <div className="grid border-t border-[var(--theme-border)] sm:grid-cols-3">
          {[
            ["01", "Chọn hồ sơ"],
            ["02", "Quyết định phí"],
            ["03", "Chờ thanh toán / ký"],
          ].map(([number, label]) => (
            <div
              className="flex items-center gap-3 border-[var(--theme-border)] px-6 py-4 sm:not-last:border-r"
              key={number}
            >
              <span className="font-mono text-xs font-bold text-primary-700">
                {number}
              </span>
              <span className="text-sm font-semibold">{label}</span>
            </div>
          ))}
        </div>
      </header>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <form
          className="space-y-6 rounded-3xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-8"
          onSubmit={(event) => {
            event.preventDefault();
            if (!valid || pending) return;
            if (mode === "PAID") issue.mutate();
            else waive.mutate();
          }}
        >
          <label className="grid gap-2 text-sm font-bold">
            Hồ sơ đã phê duyệt
            <select
              className={controlClass}
              disabled={candidates.isPending || pending}
              onChange={(event) => changeDossier(event.target.value)}
              required
              value={dossierId}
            >
              <option value="">
                {candidates.isPending ? "Đang tải hồ sơ…" : "Chọn hồ sơ"}
              </option>
              {candidates.data?.map((item) => (
                <option key={item.dossierId} value={item.dossierId}>
                  {item.dossierCode} · {item.dossierTitle}
                </option>
              ))}
            </select>
          </label>
          {candidates.isError ? (
            <p
              className="payment-feedback-error rounded-xl border p-4 text-sm"
              role="alert"
            >
              Chưa tải được danh sách hồ sơ đã phê duyệt. Vui lòng thử lại.
            </p>
          ) : null}
          {candidates.data?.length === 0 ? (
            <p className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4 text-sm text-[var(--theme-muted)]">
              Hiện không có hồ sơ nào đang chờ quyết định phí.
            </p>
          ) : null}

          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="mb-3 text-sm font-bold">
              Hình thức xử lý phí
            </legend>
            {(
              [
                [
                  "PAID",
                  "Có thu phí",
                  "Gửi số tiền và đường dẫn thanh toán",
                  BadgeDollarSign,
                ],
                [
                  "FREE",
                  "Miễn phí",
                  "Bỏ qua thanh toán và chuyển sang chờ ký",
                  Gift,
                ],
              ] as const
            ).map(([value, title, detail, Icon]) => (
              <label
                className={`payment-mode cursor-pointer rounded-2xl border p-4 transition-[border-color,background-color,transform] hover:-translate-y-0.5 ${mode === value ? "payment-mode-selected" : "border-[var(--theme-border)] bg-[var(--theme-elevated)]"}`}
                key={value}
              >
                <span className="flex items-start gap-3">
                  <input
                    aria-label={
                      title === "Miễn phí" ? "Miễn phí" : "Có thu phí"
                    }
                    checked={mode === value}
                    className="mt-1 accent-primary-700"
                    disabled={pending}
                    name="fee-mode"
                    onChange={() => changeMode(value)}
                    type="radio"
                    value={value}
                  />
                  <span>
                    <span className="flex items-center gap-2 font-bold">
                      <Icon className="size-4" />
                      {title}
                    </span>
                    <span className="mt-1 block text-sm leading-5 opacity-75">
                      {detail}
                    </span>
                  </span>
                </span>
              </label>
            ))}
          </fieldset>

          {mode === "PAID" ? (
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="grid gap-2 text-sm font-bold">
                Số tiền cần thanh toán (VND)
                <input
                  className={`${controlClass} text-lg font-bold tabular-nums`}
                  inputMode="numeric"
                  max={1_000_000_000}
                  min={1_000}
                  onChange={(event) =>
                    setAmount(event.target.value.replace(/\D/g, ""))
                  }
                  placeholder="Ví dụ: 1.500.000"
                  required
                  type="text"
                  value={amount}
                />
                {amount ? (
                  <span className="font-normal text-[var(--theme-muted)]">
                    {new Intl.NumberFormat("vi-VN").format(Number(amount))} đồng
                  </span>
                ) : null}
              </label>
              <label className="grid gap-2 text-sm font-bold">
                Hạn thanh toán (không bắt buộc)
                <input
                  className={`${controlClass} font-normal`}
                  onChange={(event) => setDueAt(event.target.value)}
                  type="datetime-local"
                  value={dueAt}
                />
              </label>
              <label className="grid gap-2 text-sm font-bold sm:col-span-2">
                Nội dung khoản phí
                <textarea
                  className={`${controlClass} min-h-28 py-3 font-normal`}
                  maxLength={255}
                  minLength={5}
                  onChange={(event) => setDescription(event.target.value)}
                  required
                  value={description}
                />
              </label>
            </div>
          ) : (
            <label className="grid gap-2 text-sm font-bold">
              Lý do miễn phí
              <textarea
                aria-label="Lý do miễn phí"
                className={`${controlClass} min-h-28 py-3 font-normal`}
                maxLength={500}
                minLength={5}
                onChange={(event) => setWaiverReason(event.target.value)}
                placeholder="Nêu rõ chính sách hoặc căn cứ miễn phí"
                required
                value={waiverReason}
              />
              <span className="font-normal text-[var(--theme-muted)]">
                Lý do được lưu trong nhật ký kiểm toán.
              </span>
            </label>
          )}

          <Button
            className="w-full sm:w-auto"
            disabled={!valid || pending}
            type="submit"
          >
            {pending ? (
              <Loader2 aria-hidden="true" className="size-4 animate-spin" />
            ) : mode === "PAID" ? (
              <BadgeDollarSign aria-hidden="true" className="size-4" />
            ) : (
              <Gift aria-hidden="true" className="size-4" />
            )}
            {pending
              ? "Đang ghi nhận…"
              : mode === "PAID"
                ? "Gửi yêu cầu thanh toán"
                : "Xác nhận miễn phí"}
          </Button>
          {error ? (
            <p
              className="payment-feedback-error rounded-xl border p-4 text-sm"
              role="alert"
            >
              Chưa thể ghi nhận quyết định phí. Hồ sơ và nội dung vẫn được giữ
              lại; vui lòng kiểm tra trạng thái rồi thử lại.
            </p>
          ) : null}
        </form>

        <aside className="h-fit space-y-4 rounded-3xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-6">
          <Clock3 className="size-6 text-primary-700" aria-hidden="true" />
          <h2 className="text-lg font-bold">Trạng thái tiếp theo</h2>
          <p className="text-sm leading-6 text-[var(--theme-muted)]">
            {mode === "PAID"
              ? "Người nộp nhận thông báo và thanh toán. Khi giao dịch được xác nhận, admin nhận thông báo để chuyển sang ký."
              : "Người nộp nhận thông báo miễn phí. Hồ sơ chuyển thẳng sang hàng đợi ký blockchain."}
          </p>
          {selected ? (
            <div className="border-t border-[var(--theme-border)] pt-4">
              <p className="font-mono text-xs font-bold text-primary-700">
                {selected.dossierCode} · V{selected.versionNo}
              </p>
              <p className="mt-2 font-semibold">{selected.dossierTitle}</p>
            </div>
          ) : null}
        </aside>
      </section>

      {success ? (
        <section
          className="payment-feedback-success flex flex-col gap-4 rounded-2xl border p-5 sm:flex-row sm:items-center sm:justify-between"
          role="status"
          aria-live="polite"
        >
          <div className="flex items-start gap-3">
            <CheckCircle2
              aria-hidden="true"
              className="mt-0.5 size-6 shrink-0"
            />
            <div>
              <h2 className="font-bold">
                {mode === "PAID"
                  ? "Đã gửi yêu cầu cho người nộp"
                  : "Hồ sơ đã sẵn sàng để ký"}
              </h2>
              <p className="mt-1 text-sm">
                {mode === "PAID" && "amountMinor" in success
                  ? `${new Intl.NumberFormat("vi-VN").format(success.amountMinor)} VND · đang chờ thanh toán`
                  : "Đã ghi nhận miễn phí và chuyển hồ sơ vào hàng đợi blockchain."}
              </p>
            </div>
          </div>
          {mode === "PAID" && "id" in success ? (
            <Link
              className="font-bold underline"
              href={`/payments/${success.id}`}
            >
              Xem yêu cầu
            </Link>
          ) : (
            <Link className="font-bold underline" href="/blockchain">
              Mở hàng đợi ký
            </Link>
          )}
        </section>
      ) : null}
    </main>
  );
}
