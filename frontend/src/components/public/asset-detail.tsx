"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, Blocks, ExternalLink, LoaderCircle } from "lucide-react";

import { publicApi } from "@/lib/api/client";

export function AssetDetail({ slug }: { slug: string }) {
  const query = useQuery({
    queryKey: ["public-asset", slug],
    queryFn: () => publicApi.asset(slug),
  });
  if (query.isPending) {
    return (
      <LoaderCircle className="mx-auto mt-24 size-7 animate-spin text-gold-300" />
    );
  }
  if (query.error || !query.data) {
    return (
      <div className="py-24 text-center text-slate-300">
        Không tìm thấy tài sản công khai.
      </div>
    );
  }
  const { asset } = query.data;
  return (
    <article className="public-theme-surface">
      <header className="relative overflow-hidden border-b border-white/10 px-4 py-16 sm:px-6 lg:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_25%,rgb(185_28_28_/_18%),transparent_28rem)]" />
        <div className="relative mx-auto max-w-7xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-gold-300/20 bg-gold-300/5 px-3 py-1 text-xs font-bold uppercase tracking-wider text-gold-300">
              {asset.categoryName}
            </span>
            <span className="flex items-center gap-1.5 text-xs font-bold text-success">
              <BadgeCheck className="size-4" />
              {asset.certificateStatus === "ACTIVE"
                ? "Chứng thư đang có hiệu lực"
                : asset.certificateStatus === "REVOKED"
                  ? "Chứng thư đã thu hồi"
                  : "Chứng thư đã hết hạn"}
            </span>
          </div>
          <h1 className="mt-7 max-w-5xl text-4xl font-bold tracking-[-0.04em] sm:text-6xl lg:text-7xl">
            {asset.title}
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-8 text-slate-400">
            {asset.summary}
          </p>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_22rem] lg:px-8">
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-8">
          <h2 className="text-xl font-bold">Thông tin công khai</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            Đây là thông tin được công bố cùng chứng thư. File gốc vẫn nằm trong
            kho lưu trữ của hệ thống, không được đưa lên blockchain.
          </p>
          <dl className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 p-4">
              <dt className="text-xs text-slate-400">Số chứng thư</dt>
              <dd className="mt-1 font-bold text-white">
                {asset.certificateNumber}
              </dd>
            </div>
            <div className="rounded-2xl border border-white/10 p-4">
              <dt className="text-xs text-slate-400">Danh mục</dt>
              <dd className="mt-1 font-bold text-white">
                {asset.categoryName}
              </dd>
            </div>
          </dl>
          <details className="mt-6 border-t border-white/10 pt-4">
            <summary className="cursor-pointer text-sm font-bold text-slate-200">
              Chi tiết nâng cao
            </summary>
            <pre className="mt-4 overflow-x-auto whitespace-pre-wrap break-words rounded-2xl bg-ink-950 p-5 text-xs leading-6 text-slate-300">
              {JSON.stringify(query.data.metadata, null, 2)}
            </pre>
          </details>
        </section>
        <aside className="h-fit rounded-3xl border border-white/10 bg-ink-900 p-6">
          <Blocks className="size-7 text-gold-300" />
          <h2 className="mt-5 font-bold">Xác minh blockchain</h2>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {asset.transactionHash
              ? "Bản ghi blockchain đã được công bố. Hãy tra cứu chứng thư để kiểm tra trạng thái mới nhất."
              : "Chưa có mã giao dịch blockchain để đối chiếu."}
          </p>
          <dl className="mt-5 space-y-4 text-xs">
            <div>
              <dt className="text-slate-500">Số chứng thư</dt>
              <dd className="mt-1 break-all font-mono text-white">
                {asset.certificateNumber}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Mạng blockchain</dt>
              <dd className="mt-1 font-bold text-white">
                {query.data.network?.includes("polygon")
                  ? "Polygon Mainnet"
                  : (query.data.network ?? "—")}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Mã giao dịch trên blockchain</dt>
              <dd className="mt-1 break-all font-mono text-white">
                {asset.transactionHash ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Số lượt mạng đã xác nhận</dt>
              <dd className="mt-1 font-mono text-white">
                {query.data.confirmations}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Địa chỉ sổ đăng ký công khai</dt>
              <dd className="mt-1 break-all font-mono text-white">
                {query.data.contractAddress ?? "—"}
              </dd>
            </div>
          </dl>
          {asset.transactionHash ? (
            <a
              className="mt-5 inline-flex min-h-11 items-center gap-2 text-sm font-bold text-gold-300"
              href={`https://polygonscan.com/tx/${asset.transactionHash}`}
              rel="noreferrer"
              target="_blank"
            >
              Mở giao dịch trên PolygonScan
              <ExternalLink className="size-4" aria-hidden="true" />
            </a>
          ) : null}
          <details className="mt-5 border-t border-white/10 pt-4">
            <summary className="cursor-pointer text-sm font-bold text-slate-200">
              Blockchain là gì?
            </summary>
            <p className="mt-3 text-sm leading-6 text-slate-400">
              Blockchain là sổ ghi nhận công khai. Hệ thống không đưa tài liệu
              gốc lên mạng; chỉ ghi lại dấu vân tay số để kiểm tra tài liệu có
              bị thay đổi hay không.
            </p>
          </details>
        </aside>
      </div>
    </article>
  );
}
