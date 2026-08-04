"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, History, RotateCcw, Vote } from "lucide-react";
import Link from "next/link";

import { votingApi } from "@/lib/api/client";
import type { VoteStatus } from "@/lib/api/types";

const statusLabel: Record<VoteStatus, string> = {
  VALID: "Đang có hiệu lực",
  SUSPICIOUS: "Đang được kiểm tra",
  REVOKED_BY_USER: "Đã thu hồi",
  INVALIDATED: "Không hợp lệ",
  REJECTED: "Đã từ chối",
};

export function VoteHistory() {
  const history = useQuery({
    queryKey: ["my-votes", 1],
    queryFn: () => votingApi.myVotes(),
  });

  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <header className="rounded-[2rem] bg-ink-950 px-6 py-8 text-white sm:px-9">
        <p className="flex items-center gap-2 text-sm font-bold text-primary-300">
          <History className="size-4" /> Dấu vết bình chọn cá nhân
        </p>
        <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
          Lịch sử bình chọn
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          Theo dõi lựa chọn hiện tại và toàn bộ thay đổi của riêng bạn. Danh
          tính người bình chọn không xuất hiện trên bảng công khai.
        </p>
      </header>

      {history.isPending ? (
        <div
          className="rounded-2xl border border-neutral-200 bg-white p-8"
          role="status"
        >
          Đang tải lịch sử bình chọn...
        </div>
      ) : null}
      {history.isError ? (
        <div
          className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800"
          role="alert"
        >
          Chưa thể tải lịch sử. Vui lòng thử lại sau.
        </div>
      ) : null}
      {history.data?.data.length === 0 ? (
        <div className="rounded-[2rem] border border-dashed border-neutral-300 bg-white p-12 text-center">
          <Vote className="mx-auto size-9 text-neutral-300" />
          <h2 className="mt-4 text-xl font-black">Bạn chưa bình chọn</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Các lựa chọn của bạn sẽ được ghi nhận minh bạch tại đây.
          </p>
          <Link
            className="mt-5 inline-flex font-bold text-primary-700"
            href="/binh-chon"
          >
            Khám phá chiến dịch
          </Link>
        </div>
      ) : null}

      <div className="grid gap-4">
        {history.data?.data.map((item) => (
          <article
            className="rounded-[1.5rem] border border-neutral-200 bg-white p-5 shadow-sm sm:p-6"
            key={item.voteId}
          >
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-primary-700">
                  {item.campaignName}
                </p>
                <h2 className="mt-2 text-xl font-black text-ink-950">
                  {item.workTitle}
                </h2>
                <time className="mt-2 block text-sm text-neutral-500">
                  {new Date(item.createdAt).toLocaleString("vi-VN")}
                </time>
              </div>
              <span className="w-fit rounded-full bg-primary-50 px-3 py-1.5 text-xs font-black text-primary-800">
                {statusLabel[item.status]}
              </span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2 border-t border-neutral-100 pt-4">
              {item.canChange ? (
                <span className="inline-flex items-center gap-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">
                  <ArrowRightLeft className="size-4" /> Có thể đổi lựa chọn
                </span>
              ) : null}
              {item.canRevoke ? (
                <span className="inline-flex items-center gap-2 rounded-xl bg-neutral-100 px-3 py-2 text-xs font-bold text-neutral-700">
                  <RotateCcw className="size-4" /> Có thể thu hồi
                </span>
              ) : null}
              <Link
                className="ml-auto inline-flex items-center text-sm font-bold text-primary-700"
                href={`/binh-chon/${item.campaignSlug}`}
              >
                Xem chiến dịch
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
