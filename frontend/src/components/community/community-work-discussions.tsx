"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { CommunityPostCard } from "@/components/community/community-post-card";
import { communityApi } from "@/lib/api/client";

export function CommunityWorkDiscussions({
  workId,
  workSlug,
  workTitle,
}: {
  workId: string;
  workSlug: string;
  workTitle: string;
}) {
  const discussions = useQuery({
    queryKey: ["community", "work-discussions", workId],
    queryFn: ({ signal }) =>
      communityApi.posts(
        { relatedWorkId: workId, page: 1, pageSize: 5, sort: "discussed" },
        signal,
      ),
    staleTime: 30_000,
  });
  const relatedWorkQuery = new URLSearchParams({ relatedWorkId: workId });
  const composeQuery = new URLSearchParams({
    relatedWorkId: workId,
    relatedWorkSlug: workSlug,
  });

  return (
    <section
      aria-labelledby="community-work-discussions-heading"
      className="mt-16 border-t border-white/10 pt-10"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
            Góc trao đổi
          </p>
          <h2
            className="mt-2 text-3xl font-bold text-white"
            id="community-work-discussions-heading"
          >
            Thảo luận cộng đồng
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
            Các bài viết dưới đây do thành viên chia sẻ, không phải nội dung xác
            minh chính thức của tác phẩm.
          </p>
        </div>
        <Link
          className="inline-flex min-h-11 items-center justify-center rounded-lg border border-white/20 px-4 text-sm font-bold text-white hover:border-gold-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-300"
          href={`/community/new?${composeQuery.toString()}`}
        >
          Viết bài thảo luận về {workTitle}
        </Link>
      </div>
      {discussions.isPending ? (
        <p
          aria-busy="true"
          className="mt-6 text-sm text-slate-400"
          role="status"
        >
          Đang tải thảo luận…
        </p>
      ) : null}
      {discussions.isError ? (
        <p className="mt-6 text-sm text-amber-200" role="status">
          Chưa thể tải thảo luận lúc này.
        </p>
      ) : null}
      {discussions.data?.data.length ? (
        <div className="mt-5 rounded-2xl border border-white/10 px-5 sm:px-7">
          {discussions.data.data.map((post) => (
            <CommunityPostCard key={post.id} post={post} />
          ))}
        </div>
      ) : null}
      {!discussions.isPending &&
      !discussions.isError &&
      !discussions.data?.data.length ? (
        <p
          className="mt-6 rounded-xl border border-white/10 p-5 text-sm text-slate-300"
          role="status"
        >
          Chưa có bài thảo luận nào liên kết với tác phẩm này.
        </p>
      ) : null}
      <Link
        className="mt-4 inline-flex min-h-10 items-center text-sm font-bold text-gold-300 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-300"
        href={`/community?${relatedWorkQuery.toString()}`}
      >
        Xem tất cả thảo luận
      </Link>
    </section>
  );
}
