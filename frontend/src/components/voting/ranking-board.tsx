"use client";

import { ChevronLeft, ChevronRight, Medal, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { rankingApi } from "@/lib/api/client";
import type { PublicRankingItem } from "@/lib/api/types";

const PAGE_SIZE = 20;

export function RankingBoard({ slug }: { slug: string }) {
  const [page, setPage] = useState(1);
  const ranking = useQuery({
    queryKey: ["public-ranking", slug, page],
    queryFn: () => rankingApi.public(slug, { page, pageSize: PAGE_SIZE }),
    staleTime: 60_000,
  });

  if (ranking.isPending) return <RankingSkeleton />;
  if (ranking.isError) {
    return (
      <section className="bg-[#131313] px-4 py-14 text-[#e5e2e1] sm:px-6 lg:px-8" aria-label="Kết quả xếp hạng">
        <div className="mx-auto max-w-[90rem] rounded-lg border border-[#5d3f3b] bg-[#1c1b1b] p-8 text-center">
          <h2 className="text-2xl font-bold">Kết quả đang được chuẩn bị</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[#c8c6c5]">
            Snapshot xếp hạng chưa được công bố cho chiến dịch này.
          </p>
        </div>
      </section>
    );
  }

  const data = ranking.data;
  if (!data || data.pagination.total === 0) {
    return (
      <section className="bg-[#131313] px-4 py-14 text-[#e5e2e1] sm:px-6 lg:px-8" aria-label="Kết quả xếp hạng">
        <div className="mx-auto max-w-[90rem] rounded-lg border border-white/10 bg-[#1c1b1b] p-8 text-center">
          <h2 className="text-2xl font-bold">Chưa có dữ liệu xếp hạng</h2>
          <p className="mt-3 text-sm leading-6 text-[#c8c6c5]">Kết quả sẽ hiển thị sau khi snapshot được tạo.</p>
        </div>
      </section>
    );
  }

  const totalPages = Math.max(1, Math.ceil(data.pagination.total / data.pagination.pageSize));
  const topThree = page === 1 ? data.items.slice(0, 3) : [];
  const listedItems = page === 1 ? data.items.slice(3) : data.items;

  return (
    <section className="bg-[#131313] px-4 py-14 text-[#e5e2e1] sm:px-6 lg:px-8" aria-labelledby="ranking-heading">
      <div className="mx-auto max-w-[90rem]">
        <div className="flex flex-col gap-6 border-b border-white/10 pb-8 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="font-mono text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-[#ffb4aa]">Kết quả đã xác minh</p>
            <h2 id="ranking-heading" className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Bảng xếp hạng</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#c8c6c5]">Thứ hạng được tính từ snapshot bất biến của chiến dịch.</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm sm:min-w-72">
            <Stat label="Phiên bản" value={`v${data.snapshot.version}`} />
            <Stat label="Lượt hợp lệ" value={data.snapshot.totalValidVotes.toLocaleString("vi-VN")} />
          </div>
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
          {topThree.map((item) => <TopRankCard item={item} key={item.workId} />)}
        </div>

        {listedItems.length > 0 ? <div className="mt-8 overflow-hidden rounded-lg border border-white/10 bg-[#1c1b1b]">
          <div className="grid grid-cols-[3.5rem_minmax(0,1fr)_5rem] gap-4 border-b border-white/10 px-4 py-3 font-mono text-[0.64rem] uppercase tracking-[0.14em] text-[#ad8883] sm:grid-cols-[5rem_minmax(0,1fr)_7rem_7rem] sm:px-6">
            <span>Hạng</span><span>Tài sản số</span><span className="text-right">Điểm</span><span className="hidden text-right sm:block">Phiếu</span>
          </div>
          <ol aria-label="Danh sách xếp hạng" className="divide-y divide-white/8">
            {listedItems.map((item) => <RankingRow item={item} key={item.workId} />)}
          </ol>
        </div> : null}

        <div className="mt-6 flex flex-col gap-4 text-xs text-[#929090] sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2"><ShieldCheck aria-hidden="true" className="size-4 text-[#ffb4aa]" /> Snapshot {data.snapshot.resultDigest.slice(0, 12)}…</p>
          <div className="flex items-center gap-3">
            <button type="button" className="inline-flex min-h-10 items-center gap-1 rounded-md border border-white/15 px-3 font-semibold text-[#e5e2e1] transition hover:border-[#ffb4aa] disabled:cursor-not-allowed disabled:opacity-40" disabled={page === 1} onClick={() => setPage((current) => Math.max(1, current - 1))} aria-label="Trang trước"><ChevronLeft aria-hidden="true" className="size-4" /> Trước</button>
            <span aria-live="polite" className="font-mono">{page} / {totalPages}</span>
            <button type="button" className="inline-flex min-h-10 items-center gap-1 rounded-md border border-white/15 px-3 font-semibold text-[#e5e2e1] transition hover:border-[#ffb4aa] disabled:cursor-not-allowed disabled:opacity-40" disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} aria-label="Trang sau">Sau <ChevronRight aria-hidden="true" className="size-4" /></button>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-white/10 bg-[#201f1f] px-3 py-3"><p className="font-mono text-[0.6rem] uppercase tracking-[0.12em] text-[#929090]">{label}</p><p className="mt-1 font-semibold text-[#fff9ef]">{value}</p></div>;
}

function TopRankCard({ item }: { item: PublicRankingItem }) {
  return <article className={item.rank === 1 ? "rounded-lg border border-[#ffb4aa]/55 bg-[#2a2a2a] p-6" : "rounded-lg border border-white/10 bg-[#1c1b1b] p-6"}><div className="flex items-center justify-between"><span className="grid size-10 place-items-center rounded-md border border-[#ffdb3c]/45 text-[#ffdb3c]"><Medal aria-hidden="true" className="size-5" /></span><span className="font-mono text-2xl font-semibold text-[#fff9ef]">{String(item.rank).padStart(2, "0")}</span></div><h3 className="mt-6 line-clamp-2 text-xl font-semibold text-[#fff9ef]">{item.title}</h3><p className="mt-2 line-clamp-2 text-sm leading-6 text-[#c8c6c5]">{item.shortDescription}</p><div className="mt-6 flex items-end justify-between border-t border-white/10 pt-4"><span className="text-xs text-[#ad8883]">{item.categoryName}</span><span className="font-mono text-lg text-[#ffdb3c]">{item.score.toLocaleString("vi-VN")}</span></div></article>;
}

function RankingRow({ item }: { item: PublicRankingItem }) {
  return <li className="grid grid-cols-[3.5rem_minmax(0,1fr)_5rem] items-center gap-4 px-4 py-4 transition hover:bg-white/[0.03] sm:grid-cols-[5rem_minmax(0,1fr)_7rem_7rem] sm:px-6"><span className="font-mono text-lg font-semibold text-[#ffb4aa]">{String(item.rank).padStart(2, "0")}</span><div className="min-w-0"><p className="truncate font-semibold text-[#fff9ef]">{item.title}</p><p className="mt-1 truncate text-xs text-[#929090]">{item.categoryName}{item.authorDisplayName ? ` · ${item.authorDisplayName}` : ""}</p></div><span className="text-right font-mono text-sm text-[#ffdb3c]">{item.score.toLocaleString("vi-VN")}</span><span className="hidden text-right font-mono text-sm text-[#c8c6c5] sm:block">{item.effectiveVoteCount.toLocaleString("vi-VN")}</span></li>;
}

function RankingSkeleton() {
  return <section className="bg-[#131313] px-4 py-14 text-[#e5e2e1] sm:px-6 lg:px-8" aria-busy="true" aria-label="Đang tải bảng xếp hạng"><div className="mx-auto max-w-[90rem] space-y-5"><div className="h-8 w-56 animate-pulse rounded bg-[#2a2a2a]" /><div className="grid gap-4 lg:grid-cols-3"><div className="h-48 animate-pulse rounded-lg bg-[#1c1b1b]" /><div className="h-48 animate-pulse rounded-lg bg-[#1c1b1b]" /><div className="h-48 animate-pulse rounded-lg bg-[#1c1b1b]" /></div><div className="h-64 animate-pulse rounded-lg bg-[#1c1b1b]" /></div></section>;
}
