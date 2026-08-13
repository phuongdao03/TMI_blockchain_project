"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  LockKeyhole,
  Search,
  ShieldCheck,
  Trash2,
  Trophy,
} from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { publicApi, votingCampaignAdminApi } from "@/lib/api/client";
import type { CampaignParticipantStatus } from "@/lib/api/types";

const statusLabels: Record<CampaignParticipantStatus, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REMOVED: "Đã gỡ",
};

export function VotingParticipantWorkspace() {
  const queryClient = useQueryClient();
  const [selectedCampaignId, setSelectedCampaignId] = useState("");
  const [reason, setReason] = useState("");
  const [searchText, setSearchText] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);

  const campaigns = useQuery({
    queryKey: ["admin-voting-campaigns"],
    queryFn: votingCampaignAdminApi.list,
  });
  const campaignId = selectedCampaignId || campaigns.data?.data[0]?.id || "";
  const campaign = campaigns.data?.data.find((item) => item.id === campaignId);
  const frozen = campaign
    ? !["DRAFT", "SCHEDULED"].includes(campaign.status)
    : true;
  const participants = useQuery({
    queryKey: ["admin-voting-participants", campaignId],
    queryFn: () => votingCampaignAdminApi.participants(campaignId),
    enabled: Boolean(campaignId),
  });
  const searchResults = useQuery({
    queryKey: ["admin-voting-work-search", submittedQuery],
    queryFn: () =>
      publicApi.search({
        q: submittedQuery,
        tags: [],
        tagsMode: "any",
        sort: "relevance",
      }),
    enabled: submittedQuery.length >= 2,
  });
  const refreshParticipants = () =>
    queryClient.invalidateQueries({
      queryKey: ["admin-voting-participants", campaignId],
    });
  const bulkAdd = useMutation({
    mutationFn: () =>
      votingCampaignAdminApi.bulkAdd(campaignId, selected, reason.trim()),
    onSuccess: async () => {
      setSelected([]);
      await refreshParticipants();
    },
  });
  const transition = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string;
      action: "approve" | "remove";
    }) =>
      votingCampaignAdminApi.transition(campaignId, id, action, reason.trim()),
    onSuccess: refreshParticipants,
  });

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    setSubmittedQuery(searchText.trim());
    setSelected([]);
  }

  const reasonReady = reason.trim().length > 0;

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <header className="overflow-hidden rounded-3xl bg-ink-950 text-white shadow-xl shadow-ink-950/10">
        <div className="grid gap-8 p-7 sm:p-9 lg:grid-cols-[1fr_22rem] lg:items-end">
          <div>
            <p className="flex items-center gap-2 text-sm font-bold text-gold-300">
              <Trophy className="size-4" /> Voting Operations
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Quản lý tác phẩm bình chọn
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Kiểm soát tập tác phẩm tham gia trước khi chiến dịch kích hoạt.
              Mọi thay đổi đều được lưu dấu kiểm toán.
            </p>
          </div>
          <label className="text-sm font-semibold text-slate-200">
            Chiến dịch
            <select
              className="mt-2 min-h-12 w-full rounded-xl border border-white/15 bg-white/10 px-4 text-white"
              onChange={(event) => setSelectedCampaignId(event.target.value)}
              value={campaignId}
            >
              {campaigns.data?.data.map((item) => (
                <option
                  className="text-neutral-950"
                  key={item.id}
                  value={item.id}
                >
                  {item.name} · {item.status}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {campaigns.isError ? (
        <ErrorPanel label="Không thể tải danh sách chiến dịch." />
      ) : null}
      {campaign ? (
        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="Trạng thái" value={campaign.status} />
          <Metric
            label="Tác phẩm"
            value={String(participants.data?.meta.total ?? 0)}
          />
          <Metric label="Phiên bản luật" value={`v${campaign.ruleVersion}`} />
        </section>
      ) : null}

      {frozen && campaign ? (
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-900">
          <LockKeyhole className="mt-0.5 size-5 shrink-0" />
          <div>
            <p className="font-bold">Tập tác phẩm đã được đóng băng</p>
            <p className="mt-1 text-sm">
              Chiến dịch {campaign.status}; chỉ có thể chỉnh sửa ở DRAFT hoặc
              SCHEDULED.
            </p>
          </div>
        </div>
      ) : null}

      <label className="block rounded-2xl border border-neutral-200 bg-white p-5 text-sm font-semibold text-neutral-800 shadow-sm">
        Lý do thao tác <span className="text-primary-700">*</span>
        <textarea
          aria-label="Lý do thao tác"
          className="mt-2 min-h-20 w-full rounded-xl border border-neutral-300 p-3 font-normal"
          maxLength={500}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Ví dụ: Đã đối chiếu điều kiện công bố và nội dung chiến dịch"
          value={reason}
        />
      </label>

      {!frozen ? (
        <section className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm sm:p-7">
          <h2 className="text-xl font-bold text-neutral-950">
            Thêm từ kho công khai
          </h2>
          <form
            className="mt-5 flex flex-col gap-3 sm:flex-row"
            onSubmit={submitSearch}
          >
            <label className="flex-1 text-sm font-semibold text-neutral-700">
              <span className="sr-only">Tìm tác phẩm công khai</span>
              <input
                aria-label="Tìm tác phẩm công khai"
                className="min-h-11 w-full rounded-xl border border-neutral-300 px-4"
                minLength={2}
                onChange={(event) => setSearchText(event.target.value)}
                placeholder="Tên tác phẩm, tác giả hoặc chứng thư"
                value={searchText}
              />
            </label>
            <Button type="submit">
              <Search className="size-4" /> Tìm kiếm
            </Button>
          </form>
          {searchResults.isError ? (
            <ErrorPanel label="Không thể tìm tác phẩm công khai." />
          ) : null}
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {searchResults.data?.data.map((work) => (
              <label
                className="flex cursor-pointer gap-3 rounded-2xl border border-neutral-200 p-4 hover:border-primary-300"
                key={work.id}
              >
                <input
                  aria-label={`Chọn ${work.title}`}
                  checked={selected.includes(work.id)}
                  className="mt-1 size-4 accent-primary-600"
                  onChange={() =>
                    setSelected((items) =>
                      items.includes(work.id)
                        ? items.filter((id) => id !== work.id)
                        : [...items, work.id],
                    )
                  }
                  type="checkbox"
                />
                <span>
                  <span className="block font-bold text-neutral-950">
                    {work.title}
                  </span>
                  <span className="mt-1 block text-xs text-neutral-500">
                    {work.categoryName} · công bố{" "}
                    {new Date(work.publishedAt).toLocaleDateString("vi-VN")}
                  </span>
                </span>
              </label>
            ))}
          </div>
          {searchResults.data?.data.length === 0 ? (
            <p className="mt-5 text-sm text-neutral-500">
              Không tìm thấy tác phẩm đủ điều kiện công khai.
            </p>
          ) : null}
          <Button
            className="mt-5"
            disabled={
              !reasonReady || selected.length === 0 || bulkAdd.isPending
            }
            onClick={() => bulkAdd.mutate()}
          >
            Thêm {selected.length} tác phẩm
          </Button>
          {bulkAdd.isError ? (
            <p className="mt-3 text-sm text-red-700" role="alert">
              Không thể thêm. Tác phẩm có thể đã bị ẩn hoặc chiến dịch đã khóa.
            </p>
          ) : null}
        </section>
      ) : null}

      <section aria-labelledby="participant-heading">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-primary-700">
              Participant registry
            </p>
            <h2 className="mt-1 text-2xl font-bold" id="participant-heading">
              Tác phẩm trong chiến dịch
            </h2>
          </div>
          <span className="text-sm text-neutral-500">
            {participants.data?.meta.total ?? 0} bản ghi
          </span>
        </div>
        {participants.isPending ? (
          <div
            aria-label="Đang tải tác phẩm"
            className="mt-5 h-32 animate-pulse rounded-2xl bg-neutral-200"
          />
        ) : null}
        {participants.isError ? (
          <ErrorPanel label="Không thể tải tác phẩm tham gia." />
        ) : null}
        {participants.data?.data.length === 0 ? (
          <div className="mt-5 rounded-3xl border border-dashed border-neutral-300 bg-white p-10 text-center">
            <ShieldCheck className="mx-auto size-8 text-primary-600" />
            <p className="mt-3 font-bold">Chưa có tác phẩm tham gia</p>
          </div>
        ) : null}
        <div className="mt-5 grid gap-3">
          {participants.data?.data.map((item) => (
            <article
              className="flex flex-col gap-4 rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between"
              key={item.id}
            >
              <div>
                <span className="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-bold text-neutral-700">
                  {statusLabels[item.status]}
                </span>
                <Link
                  className="mt-3 block text-lg font-bold text-neutral-950 hover:text-primary-700"
                  href={`/works/${item.slug}`}
                  target="_blank"
                >
                  {item.title}
                </Link>
                <p className="mt-1 text-xs text-neutral-500">
                  ID: {item.workId}
                </p>
              </div>
              {!frozen && item.status !== "REMOVED" ? (
                <div className="flex gap-2">
                  {item.status === "PENDING" ? (
                    <Button
                      aria-label={`Duyệt ${item.title}`}
                      disabled={!reasonReady || transition.isPending}
                      onClick={() =>
                        transition.mutate({ id: item.id, action: "approve" })
                      }
                    >
                      <CheckCircle2 className="size-4" /> Duyệt
                    </Button>
                  ) : null}
                  <Button
                    aria-label={`Gỡ ${item.title}`}
                    disabled={!reasonReady || transition.isPending}
                    onClick={() =>
                      transition.mutate({ id: item.id, action: "remove" })
                    }
                    variant="outline"
                  >
                    <Trash2 className="size-4" /> Gỡ
                  </Button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-bold tracking-wider text-neutral-500 uppercase">
        {label}
      </p>
      <p className="mt-2 text-2xl font-bold text-neutral-950">{value}</p>
    </div>
  );
}

function ErrorPanel({ label }: { label: string }) {
  return (
    <div
      className="mt-5 flex gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"
      role="alert"
    >
      <AlertTriangle className="size-5 shrink-0" /> {label}
    </div>
  );
}
