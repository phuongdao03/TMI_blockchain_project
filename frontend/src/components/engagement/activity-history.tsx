"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { Heart, History, LoaderCircle, Share2 } from "lucide-react";

import { activityApi } from "@/lib/api/client";

export function ActivityHistory() {
  const activity = useInfiniteQuery({
    queryKey: ["my-activity"],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) => activityApi.list(pageParam),
    getNextPageParam: (page) => page.nextCursor ?? undefined,
  });
  const items = activity.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-7">
      <header className="rounded-[2rem] bg-ink-950 px-6 py-8 text-white sm:px-9">
        <p className="flex items-center gap-2 text-sm font-bold text-primary-300">
          <History aria-hidden="true" className="size-4" /> Dấu vết hoạt động cá nhân
        </p>
        <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
          Lịch sử hoạt động
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          Chỉ bạn có thể xem các tài sản đã yêu thích và thao tác chia sẻ của mình.
        </p>
      </header>

      {activity.isPending ? (
        <div className="rounded-2xl border border-neutral-200 bg-white p-8" role="status">
          Đang tải lịch sử hoạt động...
        </div>
      ) : null}
      {activity.isError ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-red-800" role="alert">
          Chưa thể tải lịch sử hoạt động. Vui lòng thử lại sau.
        </div>
      ) : null}
      {!activity.isPending && !activity.isError && items.length === 0 ? (
        <div className="rounded-[2rem] border border-dashed border-neutral-300 bg-white p-12 text-center">
          <History aria-hidden="true" className="mx-auto size-9 text-neutral-300" />
          <h2 className="mt-4 text-xl font-black">Chưa có hoạt động</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Các lượt yêu thích và chia sẻ sau khi đăng nhập sẽ xuất hiện tại đây.
          </p>
        </div>
      ) : null}

      <div className="grid gap-4">
        {items.map((item) => (
          <article
            className="rounded-[1.5rem] border border-neutral-200 bg-white p-5 shadow-sm sm:p-6"
            key={item.activityId}
          >
            <div className="flex items-start gap-4">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary-50 text-primary-700">
                {item.kind === "FAVORITE" ? (
                  <Heart aria-hidden="true" className="size-5" />
                ) : (
                  <Share2 aria-hidden="true" className="size-5" />
                )}
              </span>
              <div className="min-w-0">
                <p className="text-xs font-black uppercase tracking-[0.16em] text-primary-700">
                  {item.kind === "FAVORITE" ? "Đã yêu thích" : `Đã chia sẻ · ${item.channel ?? ""}`}
                </p>
                <h2 className="mt-2 truncate text-xl font-black text-ink-950">
                  {item.title}
                </h2>
                <p className="mt-1 line-clamp-2 text-sm leading-6 text-neutral-500">
                  {item.shortDescription}
                </p>
                <time className="mt-2 block text-xs text-neutral-500">
                  {new Date(item.createdAt).toLocaleString("vi-VN")}
                </time>
              </div>
            </div>
          </article>
        ))}
      </div>

      {activity.hasNextPage ? (
        <button
          className="mx-auto flex min-h-11 items-center gap-2 rounded-xl border border-neutral-200 bg-white px-5 text-sm font-bold text-neutral-800 hover:border-primary-300 hover:text-primary-700 disabled:opacity-60"
          disabled={activity.isFetchingNextPage}
          onClick={() => activity.fetchNextPage()}
          type="button"
        >
          {activity.isFetchingNextPage ? <LoaderCircle className="size-4 animate-spin" /> : null}
          Tải thêm hoạt động
        </button>
      ) : null}
    </div>
  );
}
