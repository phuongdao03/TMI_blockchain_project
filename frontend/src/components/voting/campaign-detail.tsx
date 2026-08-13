"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Clock3, RotateCcw, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { authApi, votingApi } from "@/lib/api/client";
import { RankingBoard } from "@/components/voting/ranking-board";

function idempotencyKey(action: string) {
  return `${action}:${crypto.randomUUID()}`;
}

export function CampaignDetail({ slug }: { slug: string }) {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState("");
  const idempotencyKeys = useRef(new Map<string, string>());
  const keyFor = (action: string, workId: string) => {
    const fingerprint = `${action}:${workId}`;
    const existing = idempotencyKeys.current.get(fingerprint);
    if (existing) return existing;
    const created = idempotencyKey(action);
    idempotencyKeys.current.set(fingerprint, created);
    return created;
  };
  const releaseKey = (action: string, workId: string) => {
    idempotencyKeys.current.delete(`${action}:${workId}`);
  };
  const campaign = useQuery({
    queryKey: ["voting-campaign", slug],
    queryFn: () => votingApi.campaign(slug),
  });
  const works = useQuery({
    queryKey: ["voting-works", slug],
    queryFn: () => votingApi.works(slug),
  });
  const summary = useQuery({
    queryKey: ["voting-summary", slug],
    queryFn: () => votingApi.summary(slug),
  });
  const viewer = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.currentUser,
    retry: false,
  });
  const campaignId = campaign.data?.id;
  const eligibility = useQuery({
    queryKey: ["voting-eligibility", campaignId],
    queryFn: () => votingApi.eligibility(campaignId!),
    enabled: Boolean(campaignId && viewer.data),
    retry: false,
  });
  const history = useQuery({
    queryKey: ["my-votes", campaignId],
    queryFn: () => votingApi.myVotes(1, campaignId),
    enabled: Boolean(campaignId && viewer.data),
    retry: false,
  });
  const currentVote = history.data?.data.find((item) =>
    ["VALID", "SUSPICIOUS"].includes(item.status),
  );
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["voting-eligibility", campaignId],
      }),
      queryClient.invalidateQueries({ queryKey: ["my-votes", campaignId] }),
      queryClient.invalidateQueries({ queryKey: ["voting-summary", slug] }),
    ]);
  };
  const createVote = useMutation({
    mutationFn: (workId: string) =>
      votingApi.createVote(campaignId!, workId, keyFor("create", workId)),
    onSuccess: async (_result, workId) => {
      releaseKey("create", workId);
      setNotice("Lựa chọn của bạn đã được ghi nhận.");
      await refresh();
    },
  });
  const changeVote = useMutation({
    mutationFn: (workId: string) =>
      votingApi.changeVote(
        campaignId!,
        currentVote!.voteId,
        workId,
        keyFor("change", workId),
      ),
    onSuccess: async (_result, workId) => {
      releaseKey("change", workId);
      setNotice("Lựa chọn đã được thay đổi an toàn.");
      await refresh();
    },
  });
  const revokeVote = useMutation({
    mutationFn: (workId: string) =>
      votingApi.revokeVote(campaignId!, workId, keyFor("revoke", workId)),
    onSuccess: async (_result, workId) => {
      releaseKey("revoke", workId);
      setNotice("Phiếu đã được thu hồi.");
      await refresh();
    },
  });
  const pending =
    createVote.isPending || changeVote.isPending || revokeVote.isPending;
  const error = createVote.error || changeVote.error || revokeVote.error;
  const remaining = useCountdown(
    campaign.data?.serverTime,
    campaign.data?.endAt,
  );
  const counts = useMemo(
    () =>
      new Map(
        summary.data?.map((item) => [item.workId, item.effectiveCount]) ?? [],
      ),
    [summary.data],
  );

  if (campaign.isPending || works.isPending)
    return (
      <main className="min-h-screen bg-ink-950 p-10 text-white" role="status">
        Đang tải không gian bình chọn...
      </main>
    );
  if (!campaign.data || !works.data)
    return (
      <main className="min-h-screen bg-ink-950 p-10 text-red-300" role="alert">
        Chiến dịch không tồn tại hoặc chưa công khai.
      </main>
    );
  const isOpen = campaign.data.status === "ACTIVE" && remaining.total > 0;

  return (
    <main className="min-h-[calc(100dvh-5rem)] bg-[#f4f1e9] text-ink-950">
      <section className="bg-ink-950 text-white">
        <div className="mx-auto grid max-w-[90rem] gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_24rem] lg:px-8 lg:py-20">
          <div>
            <Link
              className="text-xs font-black uppercase tracking-[0.18em] text-gold-300"
              href="/voting"
            >
              ← Tất cả chiến dịch
            </Link>
            <h1 className="mt-6 max-w-4xl text-4xl font-black tracking-[-0.045em] sm:text-6xl">
              {campaign.data.name}
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-slate-300">
              {campaign.data.description}
            </p>
          </div>
          <aside className="rounded-3xl border border-white/10 bg-white/[0.06] p-6">
            <p className="flex items-center gap-2 text-sm font-bold text-gold-300">
              <Clock3 className="size-4" /> Thời gian còn lại
            </p>
            <p className="mt-4 text-3xl font-black" aria-live="polite">
              {isOpen ? remaining.label : "Đã đóng"}
            </p>
            <p className="mt-5 border-t border-white/10 pt-5 text-sm text-slate-400">
              Tối đa {campaign.data.maxVotesPerUser} lựa chọn / tài khoản
            </p>
          </aside>
        </div>
      </section>

      {campaign.data.status === "PUBLISHED" ? (
        <RankingBoard slug={slug} />
      ) : null}

      <section className="mx-auto max-w-[90rem] px-4 py-12 sm:px-6 lg:px-8">
        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.18em] text-primary-700">
              Danh sách đề cử
            </p>
            <h2 className="mt-2 text-3xl font-black">
              Chọn tác phẩm tạo dấu ấn
            </h2>
          </div>
          {eligibility.data ? (
            <span className="rounded-full bg-white px-4 py-2 text-sm font-black shadow-sm">
              Còn {eligibility.data.remainingQuota} lượt
            </span>
          ) : null}
        </div>
        {notice ? (
          <p
            className="mb-5 rounded-2xl bg-emerald-100 p-4 font-bold text-emerald-900"
            role="status"
          >
            <Check className="mr-2 inline size-5" />
            {notice}
          </p>
        ) : null}
        {error ? (
          <p
            className="mb-5 rounded-2xl bg-red-100 p-4 font-bold text-red-900"
            role="alert"
          >
            Không thể cập nhật phiếu. Quy tắc chiến dịch có thể vừa thay đổi.
          </p>
        ) : null}
        <div className="grid gap-5 lg:grid-cols-2">
          {works.data.map((work, index) => {
            const selected = currentVote?.workId === work.workId;
            return (
              <article
                className={
                  selected
                    ? "rounded-[2rem] border-2 border-primary-600 bg-white p-7 shadow-xl"
                    : "rounded-[2rem] border border-black/10 bg-white p-7 shadow-sm"
                }
                key={work.workId}
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="text-xs font-black text-neutral-400">
                    ĐỀ CỬ 0{index + 1}
                  </span>
                  {selected ? (
                    <span className="rounded-full bg-primary-100 px-3 py-1 text-xs font-black text-primary-800">
                      Lựa chọn của bạn
                    </span>
                  ) : null}
                </div>
                <h3 className="mt-8 text-2xl font-black">{work.title}</h3>
                <p className="mt-3 min-h-12 text-sm leading-6 text-neutral-600">
                  {work.shortDescription}
                </p>
                <div className="mt-7 flex items-center justify-between border-t border-neutral-100 pt-5">
                  <span className="flex items-center gap-2 text-sm font-bold text-neutral-500">
                    <Sparkles className="size-4 text-gold-500" />{" "}
                    {counts.get(work.workId) ?? 0} phiếu
                  </span>
                  {!viewer.data ? (
                    <Link
                      className="rounded-xl bg-ink-950 px-4 py-2.5 text-sm font-black text-white"
                      href={`/login?next=/voting/${slug}`}
                    >
                      Đăng nhập để chọn
                    </Link>
                  ) : null}
                  {viewer.data && selected && campaign.data.allowVoteRevoke ? (
                    <button
                      className="rounded-xl border border-neutral-300 px-4 py-2.5 text-sm font-black"
                      disabled={pending || !isOpen}
                      onClick={() => {
                        if (confirm("Thu hồi lựa chọn này?"))
                          revokeVote.mutate(work.workId);
                      }}
                      type="button"
                    >
                      <RotateCcw className="mr-2 inline size-4" />
                      Thu hồi
                    </button>
                  ) : null}
                  {viewer.data &&
                  !selected &&
                  currentVote &&
                  campaign.data.allowVoteChange ? (
                    <button
                      className="rounded-xl bg-ink-950 px-4 py-2.5 text-sm font-black text-white disabled:opacity-50"
                      disabled={pending || !isOpen}
                      onClick={() => changeVote.mutate(work.workId)}
                      type="button"
                    >
                      Đổi sang tác phẩm này
                    </button>
                  ) : null}
                  {viewer.data && !currentVote ? (
                    <button
                      className="rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-black text-white disabled:opacity-50"
                      disabled={
                        pending ||
                        !isOpen ||
                        eligibility.data?.canVote === false
                      }
                      onClick={() => createVote.mutate(work.workId)}
                      type="button"
                    >
                      Bình chọn
                    </button>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
        <p className="mt-8 flex items-center gap-2 text-xs text-neutral-500">
          <ShieldCheck className="size-4" /> Số liệu cập nhật gần nhất:{" "}
          {summary.data?.[0]
            ? new Date(summary.data[0].refreshedAt).toLocaleString("vi-VN")
            : "đang đồng bộ"}
          .
        </p>
      </section>
    </main>
  );
}

function useCountdown(serverTime?: string, endAt?: string) {
  const [currentTime, setCurrentTime] = useState(0);
  useEffect(() => {
    if (!serverTime) return;
    const serverStart = Date.parse(serverTime);
    const clientStart = Date.now();
    const update = () => setCurrentTime(serverStart + Date.now() - clientStart);
    update();
    const timer = window.setInterval(update, 1_000);
    return () => window.clearInterval(timer);
  }, [serverTime]);
  const total = Math.max(
    0,
    (endAt ? Date.parse(endAt) : currentTime) - currentTime,
  );
  const days = Math.floor(total / 86_400_000);
  const hours = Math.floor((total % 86_400_000) / 3_600_000);
  const minutes = Math.floor((total % 3_600_000) / 60_000);
  return { total, label: `${days} ngày ${hours} giờ ${minutes} phút` };
}
