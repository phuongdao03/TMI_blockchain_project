"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, LoaderCircle, Search, ShieldQuestion } from "lucide-react";
import { useState } from "react";

import { publicApi } from "@/lib/api/client";

const labels = {
  VALID: ["Hợp lệ", "text-emerald-300", CheckCircle2],
  MISMATCH: ["Dữ liệu không khớp", "text-red-300", AlertTriangle],
  REVOKED: ["Đã thu hồi", "text-red-300", AlertTriangle],
  EXPIRED: ["Đã hết hạn", "text-amber-300", AlertTriangle],
  PENDING: ["Đang chờ blockchain", "text-amber-300", LoaderCircle],
  NOT_FOUND: ["Không tìm thấy", "text-slate-300", ShieldQuestion],
} as const;

export function VerificationPanel({ token }: { token?: string }) {
  const [mode, setMode] = useState<"number" | "transaction">("number");
  const [value, setValue] = useState("");
  const [lookup, setLookup] = useState(token ?? "");
  const result = useQuery({
    queryKey: ["public-verification", token ? "token" : mode, lookup],
    queryFn: () =>
      token
        ? publicApi.verifyToken(token)
        : mode === "number"
          ? publicApi.verifyNumber(lookup)
          : publicApi.verifyTransaction(lookup),
    enabled: Boolean(lookup),
    retry: false,
  });
  const presentation = result.data ? labels[result.data.status] : undefined;
  const Icon = presentation?.[2];
  return (
    <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <section className="rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-8">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">Tra cứu độc lập</p>
        <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Xác minh chứng thư</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Đối chiếu hash dữ liệu với bản ghi blockchain mà không hiển thị thông tin riêng tư.
        </p>
        {!token && (
          <form
            className="mt-7 space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              setLookup(value.trim());
            }}
          >
            <div className="grid grid-cols-2 rounded-xl bg-ink-950 p-1">
              <button className={`min-h-10 rounded-lg text-xs font-bold ${mode === "number" ? "bg-white text-ink-950" : "text-slate-400"}`} onClick={() => setMode("number")} type="button">
                Số chứng thư
              </button>
              <button className={`min-h-10 rounded-lg text-xs font-bold ${mode === "transaction" ? "bg-white text-ink-950" : "text-slate-400"}`} onClick={() => setMode("transaction")} type="button">
                Transaction hash
              </button>
            </div>
            <input
              className="min-h-12 w-full rounded-xl border border-white/10 bg-ink-950 px-4 font-mono text-sm text-white"
              onChange={(event) => setValue(event.target.value)}
              placeholder={mode === "number" ? "TMI-2026-…" : "0x…"}
              value={value}
            />
            <button className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary-600 text-sm font-bold" type="submit">
              <Search className="size-4" /> Xác minh ngay
            </button>
          </form>
        )}
      </section>
      <section aria-live="polite" className="rounded-3xl border border-white/10 bg-ink-900 p-6 sm:p-8">
        {result.isFetching ? (
          <div className="grid min-h-72 place-items-center"><LoaderCircle className="size-7 animate-spin text-gold-300" /></div>
        ) : result.error ? (
          <div className="grid min-h-72 place-items-center text-center text-red-300">Không thể kết nối dịch vụ xác minh.</div>
        ) : result.data && presentation && Icon ? (
          <div>
            <Icon className={`size-12 ${presentation[1]} ${result.data.status === "PENDING" ? "animate-spin" : ""}`} />
            <p className={`mt-5 text-xs font-bold uppercase tracking-[0.18em] ${presentation[1]}`}>Kết quả xác minh</p>
            <h2 className="mt-2 text-3xl font-bold">{presentation[0]}</h2>
            <dl className="mt-7 grid gap-4 text-sm">
              {[
                ["Chứng thư", result.data.certificateNumber],
                ["Tài sản", result.data.assetTitle],
                ["Danh mục", result.data.categoryName],
                ["Mạng", result.data.network],
                ["Giao dịch", result.data.transactionHash],
              ].map(([label, data]) => data && (
                <div className="grid gap-1 border-b border-white/10 pb-3 sm:grid-cols-[8rem_1fr]" key={label}>
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="break-all font-mono text-slate-200">{data}</dd>
                </div>
              ))}
            </dl>
            {result.data.explorerUrl && (
              <a
                className="mt-6 inline-flex min-h-11 items-center rounded-xl border border-white/15 px-4 text-sm font-bold text-white hover:bg-white/5"
                href={result.data.explorerUrl}
                rel="noreferrer"
                target="_blank"
              >
                Mở blockchain explorer
              </a>
            )}
          </div>
        ) : (
          <div className="grid min-h-72 place-items-center text-center">
            <div>
              <ShieldQuestion className="mx-auto size-10 text-slate-600" />
              <p className="mt-4 text-sm text-slate-400">Nhập mã để bắt đầu đối chiếu.</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
