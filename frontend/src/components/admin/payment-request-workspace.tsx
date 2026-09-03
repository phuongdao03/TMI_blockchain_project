"use client";

import { useMutation } from "@tanstack/react-query";
import {
  BadgeDollarSign,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { paymentApi } from "@/lib/api/client";

function requestKey() {
  return globalThis.crypto?.randomUUID?.() ?? `payment-issue-${Date.now()}`;
}

export function PaymentRequestWorkspace() {
  const [dossierId, setDossierId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState(
    "Phí xác lập và phát hành chứng thư",
  );
  const [dueAt, setDueAt] = useState("");
  const idempotencyKey = useRef(requestKey());
  const issue = useMutation({
    mutationFn: () =>
      paymentApi.issue(
        dossierId.trim(),
        {
          amountMinor: Number(amount),
          currency: "VND",
          description: description.trim(),
          ...(dueAt ? { dueAt: new Date(dueAt).toISOString() } : {}),
        },
        idempotencyKey.current,
      ),
  });
  const valid =
    /^[0-9a-f-]{36}$/i.test(dossierId.trim()) &&
    Number.isInteger(Number(amount)) &&
    Number(amount) >= 1_000 &&
    Number(amount) <= 1_000_000_000 &&
    description.trim().length >= 5;

  return (
    <main className="mx-auto max-w-5xl space-y-6">
      <header className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-8">
        <p className="font-mono text-xs font-bold uppercase tracking-[0.18em] text-primary-700">
          Thu phí hồ sơ
        </p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
          Tạo yêu cầu thanh toán
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--theme-muted)] sm:text-base">
          Tạo khoản phí cho hồ sơ đã được phê duyệt. Người nộp sẽ nhận thông báo
          và đường dẫn thanh toán ngay sau khi yêu cầu được gửi.
        </p>
      </header>

      <section className="grid gap-6 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-8 lg:grid-cols-[1fr_18rem]">
        <form
          className="grid gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (valid) issue.mutate();
          }}
        >
          <label className="grid gap-2 text-sm font-bold">
            Mã hồ sơ
            <input
              autoComplete="off"
              className="min-h-12 rounded-lg border px-4 font-mono text-sm"
              onChange={(event) => setDossierId(event.target.value)}
              placeholder="Nhập mã hồ sơ đã được phê duyệt"
              required
              value={dossierId}
            />
          </label>
          <label className="grid gap-2 text-sm font-bold">
            Số tiền cần thanh toán (VND)
            <input
              className="min-h-12 rounded-lg border px-4 text-lg font-bold tabular-nums"
              inputMode="numeric"
              max={1_000_000_000}
              min={1_000}
              onChange={(event) =>
                setAmount(event.target.value.replace(/\D/g, ""))
              }
              placeholder="Ví dụ: 1500000"
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
            Nội dung khoản phí
            <textarea
              className="min-h-24 rounded-lg border p-4 font-normal"
              maxLength={255}
              minLength={5}
              onChange={(event) => setDescription(event.target.value)}
              required
              value={description}
            />
          </label>
          <label className="grid gap-2 text-sm font-bold">
            Hạn thanh toán (không bắt buộc)
            <input
              className="min-h-12 rounded-lg border px-4 font-normal"
              onChange={(event) => setDueAt(event.target.value)}
              type="datetime-local"
              value={dueAt}
            />
          </label>
          <Button disabled={!valid || issue.isPending} type="submit">
            <BadgeDollarSign aria-hidden="true" className="size-4" />
            {issue.isPending ? "Đang tạo yêu cầu…" : "Gửi yêu cầu thanh toán"}
          </Button>
          {issue.error ? (
            <p
              className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800"
              role="alert"
            >
              Chưa thể tạo yêu cầu thanh toán. Hãy kiểm tra mã hồ sơ, trạng thái
              phê duyệt và số tiền rồi thử lại.
            </p>
          ) : null}
        </form>

        <aside className="h-fit rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-5">
          <ShieldCheck aria-hidden="true" className="size-7 text-primary-700" />
          <h2 className="mt-4 font-bold">Kiểm soát trước khi gửi</h2>
          <ol className="mt-3 space-y-3 text-sm leading-6 text-[var(--theme-muted)]">
            <li>1. Hồ sơ đã ở trạng thái phê duyệt.</li>
            <li>2. Số tiền và nội dung phí đã được xác nhận.</li>
            <li>3. Người nộp sẽ nhận thông báo và đường dẫn thanh toán.</li>
          </ol>
        </aside>
      </section>

      {issue.data ? (
        <section
          className="flex flex-col gap-4 rounded-2xl border border-emerald-300 bg-emerald-50 p-5 text-emerald-950 sm:flex-row sm:items-center sm:justify-between"
          role="status"
        >
          <div className="flex items-start gap-3">
            <CheckCircle2
              aria-hidden="true"
              className="mt-0.5 size-6 shrink-0"
            />
            <div>
              <h2 className="font-bold">Đã gửi yêu cầu cho người nộp</h2>
              <p className="mt-1 text-sm">
                Mã thanh toán {issue.data.orderCode} ·{" "}
                {new Intl.NumberFormat("vi-VN").format(issue.data.amountMinor)}{" "}
                VND
              </p>
            </div>
          </div>
          <Link
            className="inline-flex min-h-11 items-center gap-2 font-bold underline"
            href={`/payments/${issue.data.id}`}
          >
            Xem yêu cầu <ExternalLink aria-hidden="true" className="size-4" />
          </Link>
        </section>
      ) : null}
    </main>
  );
}
