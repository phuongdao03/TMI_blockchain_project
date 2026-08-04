"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Gauge,
  MousePointerClick,
  Search,
  SearchX,
} from "lucide-react";
import { useMemo, useState } from "react";

import { searchAnalyticsApi } from "@/lib/api/client";

function dateValue(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function asStart(value: string): string {
  return `${value}T00:00:00.000Z`;
}

function asExclusiveEnd(value: string): string {
  const date = new Date(`${value}T00:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString();
}

export function SearchAnalyticsDashboard() {
  const defaults = useMemo(() => {
    const end = new Date();
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - 29);
    return { start: dateValue(start), end: dateValue(end) };
  }, []);
  const [start, setStart] = useState(defaults.start);
  const [end, setEnd] = useState(defaults.end);
  const [category, setCategory] = useState("");
  const analytics = useQuery({
    queryKey: ["admin", "search-analytics", start, end, category],
    queryFn: () =>
      searchAnalyticsApi.get({
        start: asStart(start),
        end: asExclusiveEnd(end),
        category: category || undefined,
      }),
  });
  const cards = analytics.data
    ? [
        {
          label: "Lượt tìm kiếm",
          value: analytics.data.searchCount.toLocaleString("vi-VN"),
          icon: Search,
        },
        {
          label: "Không có kết quả",
          value: analytics.data.zeroResultRate.toLocaleString("vi-VN", {
            style: "percent",
            maximumFractionDigits: 1,
          }),
          icon: SearchX,
        },
        {
          label: "Tỷ lệ nhấp",
          value: analytics.data.clickThroughRate.toLocaleString("vi-VN", {
            style: "percent",
            maximumFractionDigits: 1,
          }),
          icon: MousePointerClick,
        },
        {
          label: "Độ trễ P95",
          value: `${analytics.data.latencyP95Ms} ms`,
          icon: Gauge,
        },
      ]
    : [];

  return (
    <main className="mx-auto max-w-7xl space-y-8">
      <header className="overflow-hidden rounded-[2rem] bg-ink-950 p-7 text-white shadow-2xl shadow-slate-950/10 sm:p-10">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <p className="flex items-center gap-2 text-xs font-bold tracking-[0.2em] text-gold-300 uppercase">
              <Activity className="size-4" /> Search intelligence
            </p>
            <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">
              Hiểu nhu cầu tra cứu, không đánh đổi riêng tư.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300">
              Dashboard chỉ sử dụng snapshot tổng hợp. Cụm từ tìm kiếm, danh
              tính và phiên người dùng không xuất hiện trong báo cáo quản trị.
            </p>
          </div>
          <div className="flex flex-col items-end gap-3">
            <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-4 py-2 text-xs font-bold text-emerald-200">
              AGGREGATE ONLY
            </span>
            <a
              className="rounded-xl border border-white/15 px-4 py-2 text-sm font-bold text-white transition hover:bg-white/10"
              href={searchAnalyticsApi.exportUrl({
                start: asStart(start),
                end: asExclusiveEnd(end),
                category: category || undefined,
              })}
            >
              Xuất CSV tổng hợp
            </a>
          </div>
        </div>
      </header>
      <section
        aria-label="Bộ lọc báo cáo"
        className="grid gap-4 rounded-2xl border border-neutral-200 bg-white p-5 md:grid-cols-3"
      >
        <label className="grid gap-2 text-sm font-semibold">
          Từ ngày
          <input
            className="min-h-11 rounded-xl border border-neutral-200 px-3"
            max={end}
            onChange={(event) => setStart(event.target.value)}
            type="date"
            value={start}
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Đến ngày
          <input
            className="min-h-11 rounded-xl border border-neutral-200 px-3"
            min={start}
            onChange={(event) => setEnd(event.target.value)}
            type="date"
            value={end}
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Danh mục
          <input
            className="min-h-11 rounded-xl border border-neutral-200 px-3"
            maxLength={180}
            onChange={(event) => setCategory(event.target.value)}
            placeholder="Tất cả danh mục"
            value={category}
          />
        </label>
      </section>
      {analytics.isPending ? (
        <p role="status">Đang tổng hợp snapshot tìm kiếm...</p>
      ) : null}
      {analytics.error ? (
        <p className="text-error" role="alert">
          Không thể tải phân tích tìm kiếm.
        </p>
      ) : null}
      {analytics.data ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {cards.map(({ label, value, icon: Icon }) => (
              <article
                className="rounded-2xl border border-neutral-200 bg-white p-5"
                key={label}
              >
                <Icon className="size-5 text-primary-700" />
                <p className="mt-6 text-3xl font-bold tracking-tight text-ink-950">
                  {value}
                </p>
                <p className="mt-1 text-sm text-neutral-600">{label}</p>
              </article>
            ))}
          </section>
          <section className="rounded-2xl border border-neutral-200 bg-white p-6">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-xs font-bold tracking-[0.18em] text-primary-700 uppercase">
                  Xu hướng theo ngày
                </p>
                <h2 className="mt-2 text-2xl font-bold">Hiệu suất tìm kiếm</h2>
              </div>
              <span className="text-sm text-neutral-500">
                {analytics.data.points.length} snapshot
              </span>
            </div>
            <div className="mt-6 overflow-x-auto">
              <table className="w-full min-w-[44rem] text-left text-sm">
                <thead className="border-b border-neutral-200 text-neutral-500">
                  <tr>
                    <th className="py-3">Ngày</th>
                    <th>Tìm kiếm</th>
                    <th>Zero result</th>
                    <th>Click</th>
                    <th>P95</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.data.points.map((point) => (
                    <tr
                      className="border-b border-neutral-100"
                      key={`${point.periodStart}-${point.categorySlug ?? "all"}`}
                    >
                      <td className="py-4 font-semibold">
                        {new Intl.DateTimeFormat("vi-VN", {
                          dateStyle: "medium",
                        }).format(new Date(point.periodStart))}
                      </td>
                      <td>{point.searchCount}</td>
                      <td>{point.zeroResultCount}</td>
                      <td>{point.clickCount}</td>
                      <td>{point.latencyP95Ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      ) : null}
    </main>
  );
}
