"use client";

import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, Blocks, LoaderCircle } from "lucide-react";

import { publicApi } from "@/lib/api/client";

export function AssetDetail({ slug }: { slug: string }) {
  const query = useQuery({
    queryKey: ["public-asset", slug],
    queryFn: () => publicApi.asset(slug),
  });
  if (query.isPending) {
    return <LoaderCircle className="mx-auto mt-24 size-7 animate-spin text-gold-300" />;
  }
  if (query.error || !query.data) {
    return <div className="py-24 text-center text-slate-300">Không tìm thấy tài sản công khai.</div>;
  }
  const { asset } = query.data;
  return (
    <article>
      <header className="relative overflow-hidden border-b border-white/10 px-4 py-16 sm:px-6 lg:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_78%_25%,rgb(185_28_28_/_18%),transparent_28rem)]" />
        <div className="relative mx-auto max-w-7xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full border border-gold-300/20 bg-gold-300/5 px-3 py-1 text-xs font-bold uppercase tracking-wider text-gold-300">{asset.categoryName}</span>
            <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-300"><BadgeCheck className="size-4" /> {asset.certificateStatus}</span>
          </div>
          <h1 className="mt-7 max-w-5xl text-4xl font-bold tracking-[-0.04em] sm:text-6xl lg:text-7xl">{asset.title}</h1>
          <p className="mt-6 max-w-3xl text-base leading-8 text-slate-400">{asset.summary}</p>
        </div>
      </header>
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_22rem] lg:px-8">
        <section className="rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-8">
          <h2 className="text-xl font-bold">Thông tin xác lập công khai</h2>
          <pre className="mt-6 overflow-x-auto whitespace-pre-wrap break-words rounded-2xl bg-ink-950 p-5 text-xs leading-6 text-slate-300">
            {JSON.stringify(query.data.metadata, null, 2)}
          </pre>
        </section>
        <aside className="h-fit rounded-3xl border border-white/10 bg-ink-900 p-6">
          <Blocks className="size-7 text-gold-300" />
          <h2 className="mt-5 font-bold">Dấu vết blockchain</h2>
          <dl className="mt-5 space-y-4 text-xs">
            <div><dt className="text-slate-500">Số chứng thư</dt><dd className="mt-1 break-all font-mono text-white">{asset.certificateNumber}</dd></div>
            <div><dt className="text-slate-500">Mạng</dt><dd className="mt-1 font-mono text-white">{query.data.network ?? "—"}</dd></div>
            <div><dt className="text-slate-500">Transaction</dt><dd className="mt-1 break-all font-mono text-white">{asset.transactionHash ?? "—"}</dd></div>
            <div><dt className="text-slate-500">Confirmations</dt><dd className="mt-1 font-mono text-white">{query.data.confirmations}</dd></div>
          </dl>
        </aside>
      </div>
    </article>
  );
}
