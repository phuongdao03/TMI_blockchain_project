"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CalendarDays, Trophy } from "lucide-react";
import Link from "next/link";

import { votingApi } from "@/lib/api/client";

export function CampaignList() {
  const campaigns = useQuery({
    queryKey: ["public-voting-campaigns", 1],
    queryFn: () => votingApi.campaigns(),
  });

  return (
    <main className="min-h-[calc(100dvh-5rem)] bg-ink-950 text-white">
      <section className="mx-auto max-w-[90rem] px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="grid gap-10 border-b border-white/10 pb-14 lg:grid-cols-[1fr_24rem] lg:items-end">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-gold-300">
              TMI community signal
            </p>
            <h1 className="mt-5 max-w-4xl text-5xl font-black tracking-[-0.05em] sm:text-7xl">
              Bình chọn giá trị.
              <span className="block text-slate-500">Ghi nhận minh bạch.</span>
            </h1>
          </div>
          <p className="border-l border-gold-300/40 pl-5 text-sm leading-7 text-slate-300">
            Mỗi tài khoản đã xác minh bình chọn theo quota của chiến dịch. Kết quả
            công khai không tiết lộ danh tính người tham gia.
          </p>
        </div>

        {campaigns.isPending ? <p className="py-16" role="status">Đang tải chiến dịch...</p> : null}
        {campaigns.isError ? <p className="py-16 text-red-300" role="alert">Chưa thể tải chiến dịch bình chọn.</p> : null}
        {campaigns.data?.data.length === 0 ? (
          <div className="my-12 rounded-3xl border border-dashed border-white/20 p-12 text-center text-slate-300">
            Chưa có chiến dịch công khai.
          </div>
        ) : null}
        <div className="mt-10 grid gap-5 lg:grid-cols-2">
          {campaigns.data?.data.map((campaign, index) => (
            <Link
              className="group relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.05] p-7 transition hover:-translate-y-1 hover:border-gold-300/50 sm:p-9"
              href={`/binh-chon/${campaign.slug}`}
              key={campaign.id}
            >
              <div className="flex items-start justify-between gap-5">
                <span className="grid size-12 place-items-center rounded-2xl bg-gold-300 text-ink-950">
                  <Trophy className="size-5" />
                </span>
                <span className="text-xs font-black text-slate-500">0{index + 1}</span>
              </div>
              <h2 className="mt-10 text-2xl font-black sm:text-3xl">{campaign.name}</h2>
              <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-400">{campaign.description}</p>
              <div className="mt-8 flex items-center justify-between border-t border-white/10 pt-5 text-sm">
                <span className="flex items-center gap-2 text-slate-300">
                  <CalendarDays className="size-4 text-gold-300" />
                  {new Date(campaign.endAt).toLocaleDateString("vi-VN")}
                </span>
                <ArrowUpRight className="size-5 transition group-hover:-translate-y-1 group-hover:translate-x-1" />
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
