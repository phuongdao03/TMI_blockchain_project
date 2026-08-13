"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, History, ShieldCheck, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { searchHistoryApi } from "@/lib/api/client";

const QUERY_KEY = ["search-history"] as const;

export function RecentSearchHistory({
  currentQuery,
  resultsReady,
}: {
  currentQuery?: string;
  resultsReady: boolean;
}) {
  const queryClient = useQueryClient();
  const recordedQuery = useRef<string | null>(null);
  const history = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => searchHistoryApi.get(),
  });
  const consent = useMutation({
    mutationFn: (isEnabled: boolean) => searchHistoryApi.setConsent(isEnabled),
    onSuccess: (data) => queryClient.setQueryData(QUERY_KEY, data),
  });
  const clear = useMutation({
    mutationFn: () => searchHistoryApi.clear(),
    onSuccess: () =>
      queryClient.setQueryData(QUERY_KEY, (current: typeof history.data) =>
        current ? { ...current, items: [] } : current,
      ),
  });
  const { isError: recordFailed, mutate: recordSearch } = useMutation({
    mutationFn: (query: string) => searchHistoryApi.record(query),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: QUERY_KEY }),
  });

  useEffect(() => {
    const normalized = currentQuery?.trim();
    if (
      !resultsReady ||
      !history.data?.isEnabled ||
      !normalized ||
      normalized.length < 2 ||
      recordedQuery.current === normalized
    ) {
      return;
    }
    recordedQuery.current = normalized;
    recordSearch(normalized);
  }, [currentQuery, history.data?.isEnabled, recordSearch, resultsReady]);

  if (history.isPending) {
    return (
      <div
        aria-label="Đang tải lịch sử tìm kiếm"
        className="mt-4 h-11 animate-pulse border-y border-white/[0.06] bg-white/[0.02]"
      />
    );
  }
  if (history.isError) {
    return null;
  }
  if (!history.data.isEnabled) {
    return (
      <section className="mt-4 flex flex-col gap-3 border-y border-white/[0.06] py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <ShieldCheck
            aria-hidden="true"
            className="mt-0.5 size-4 text-gold-300"
          />
          <div>
            <h2 className="text-sm font-semibold text-white">
              Lịch sử đang tắt
            </h2>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Chỉ lưu từ khóa sau khi bạn đồng ý. Có thể xóa hoặc tắt bất kỳ lúc
              nào.
            </p>
            {consent.isError ? <ActionError /> : null}
          </div>
        </div>
        <Button
          disabled={consent.isPending}
          onClick={() => consent.mutate(true)}
          type="button"
          variant="outline"
        >
          <History aria-hidden="true" className="size-4" /> Bật lịch sử tìm kiếm
        </Button>
      </section>
    );
  }

  return (
    <section
      aria-labelledby="recent-searches-heading"
      className="mt-4 border-y border-white/[0.06] py-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2
          className="flex items-center gap-2 text-xs font-bold tracking-[0.14em] text-slate-400 uppercase"
          id="recent-searches-heading"
        >
          <Clock3 aria-hidden="true" className="size-4 text-gold-300" /> Tìm
          kiếm gần đây
        </h2>
        <div className="flex items-center gap-2">
          {history.data.items.length ? (
            <button
              className="inline-flex min-h-9 items-center gap-1.5 px-2 text-xs font-semibold text-slate-500 transition hover:text-white"
              disabled={clear.isPending}
              onClick={() => clear.mutate()}
              type="button"
            >
              <Trash2 aria-hidden="true" className="size-3.5" /> Xóa lịch sử
            </button>
          ) : null}
          <button
            className="min-h-9 px-2 text-xs font-semibold text-slate-500 transition hover:text-white"
            disabled={consent.isPending}
            onClick={() => consent.mutate(false)}
            type="button"
          >
            Tắt lưu
          </button>
        </div>
      </div>
      {history.data.items.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {history.data.items.map((item) => (
            <Link
              className="inline-flex min-h-9 items-center rounded-full border border-white/10 bg-white/[0.025] px-3 text-xs font-medium text-slate-300 transition hover:border-gold-300/30 hover:text-gold-200"
              href={historyHref(item.displayQuery)}
              key={item.id}
            >
              {item.displayQuery}
            </Link>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">
          Chưa có từ khóa nào được lưu.
        </p>
      )}
      {consent.isError || clear.isError || recordFailed ? (
        <ActionError />
      ) : null}
    </section>
  );
}

function ActionError() {
  return (
    <p className="mt-2 text-xs font-medium text-red-300" role="alert">
      Chưa thể cập nhật lịch sử. Vui lòng thử lại.
    </p>
  );
}

function historyHref(query: string) {
  const parameters = new URLSearchParams({ q: query, sort: "relevance" });
  return `/search?${parameters.toString()}`;
}
