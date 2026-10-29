"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { promotionApi } from "@/lib/api/client";
import type { PromotionStats } from "@/lib/api/promotion-types";
import { formatVnd } from "@/lib/wallet/summary";
import { Choice, readableError, TextField } from "./form-fields";
import styles from "./promotions.module.css";

export function PromotionMetrics({ data }: { data: PromotionStats }) {
  return (
    <div className={styles.grid}>
      {[
        ["Chiến dịch", data.campaignCount],
        ["Đang hoạt động", data.activeCampaignCount],
        ["Voucher đã cấp", data.issuedCount],
        ["Còn hiệu lực", data.availableCount],
        ["Đã sử dụng", data.redeemedCount],
        ["Đã hết hạn", data.expiredCount],
        ["Giá trị danh nghĩa đã cấp", formatVnd(data.issuedValueVnd ?? 0)],
        ["Đang giữ cho thanh toán", formatVnd(data.reservedVnd ?? 0)],
        ["Giảm giá thực tế", formatVnd(data.discountVnd ?? 0)],
        ["Doanh thu thực thu liên quan", formatVnd(data.revenueVnd ?? 0)],
        [
          "Ngân sách còn lại",
          data.budgetRemainingVnd == null
            ? "Không giới hạn"
            : formatVnd(data.budgetRemainingVnd),
        ],
        [
          "Tỷ lệ sử dụng",
          `${data.issuedCount ? Math.round((data.redeemedCount / data.issuedCount) * 100) : 0}%`,
        ],
      ].map(([label, value]) => (
        <div className={styles.metric} key={label}>
          <strong>{value ?? 0}</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}
function downloadReport(blob: Blob) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "bao-cao-voucher.csv";
  link.click();
  URL.revokeObjectURL(url);
}
export function PromotionReports({
  initialId,
  history = false,
}: {
  initialId?: string;
  history?: boolean;
}) {
  const [id, setId] = useState(initialId ?? "");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const campaigns = useQuery({
    queryKey: ["promotions", "select"],
    queryFn: () => promotionApi.list("pageSize=100"),
  });
  const params = new URLSearchParams();
  if (start) params.set("startDate", `${start}T00:00:00+07:00`);
  if (end)
    params.set(
      "endDate",
      new Date(Date.parse(`${end}T00:00:00+07:00`) + 86400000).toISOString(),
    );
  const exportReport = useMutation({
    mutationFn: () => {
      const filters = new URLSearchParams(params);
      if (id) filters.set("campaignId", id);
      return promotionApi.exportReport(filters.toString());
    },
    onSuccess: downloadReport,
  });
  const stats = useQuery({
    queryKey: ["promotions", "stats", id, start, end],
    queryFn: () => promotionApi.stats(id || undefined, params.toString()),
  });
  const redemptions = useQuery({
    queryKey: ["promotions", "redemptions", id],
    queryFn: () => promotionApi.redemptions(id),
    enabled: Boolean(id),
  });
  const rows =
    start || end
      ? (stats.data?.transactions ?? [])
      : (redemptions.data?.items ?? stats.data?.transactions ?? []);
  return (
    <div className={styles.stack}>
      <div className={`${styles.panel} ${styles.grid}`}>
        <Choice
          label="Chiến dịch"
          value={id}
          onChange={(e) => setId(e.target.value)}
        >
          <option value="">Tất cả chiến dịch</option>
          {campaigns.data?.items.map((c) => (
            <option value={c.id} key={c.id}>
              {c.name}
            </option>
          ))}
        </Choice>
        <TextField
          label="Từ ngày"
          type="date"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <TextField
          label="Đến ngày"
          type="date"
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />
      </div>
      {stats.isPending && <p role="status">Đang tải số liệu…</p>}
      {stats.isError && (
        <p role="alert" className={styles.error}>
          {readableError(stats.error)}
        </p>
      )}
      {!history && stats.data && (
        <>
          <PromotionMetrics data={stats.data} />
          <section className={styles.panel}>
            <h2>Phễu ưu đãi</h2>
            <p className={styles.muted}>
              Đã cấp {stats.data.issuedCount} → Đã xem {stats.data.viewCount} →
              Đã bấm {stats.data.clickCount} → Đã sử dụng{" "}
              {stats.data.redeemedCount}
            </p>
            <div className={styles.chart}>
              {stats.data.daily?.map((day) => (
                <div key={day.date} className={styles.chartRow}>
                  <span>{day.date}</span>
                  <div
                    className={styles.bar}
                    style={{
                      width: `${Math.max(1, (day.issued / Math.max(1, ...(stats.data.daily ?? []).map((row) => row.issued))) * 100)}%`,
                    }}
                  />
                  <span>
                    {day.issued} / {day.redeemed}
                  </span>
                </div>
              ))}
            </div>
            <p className={styles.muted}>
              Theo ngày: số cấp / số sử dụng. Doanh thu liên quan không đồng
              nghĩa toàn bộ doanh thu tăng thêm do voucher.
            </p>
          </section>
        </>
      )}
      {exportReport.isError && (
        <p role="alert">{readableError(exportReport.error)}</p>
      )}
      <section className={styles.panel}>
        <div className={styles.heading}>
          <h2>Giao dịch sử dụng voucher</h2>
          <button
            className={styles.link}
            disabled={!rows.length || exportReport.isPending}
            onClick={() => exportReport.mutate()}
          >
            Xuất CSV
          </button>
        </div>
        <div className={styles.table}>
          <table>
            <thead>
              <tr>
                <th>Đơn hàng</th>
                <th>Giảm giá</th>
                <th>Doanh thu</th>
                <th>Trạng thái</th>
                <th>Thời điểm</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td className="break-all">{row.orderId}</td>
                  <td>{formatVnd(row.discountVnd)}</td>
                  <td>{formatVnd(row.revenueVnd ?? 0)}</td>
                  <td>{row.status}</td>
                  <td>
                    {row.redeemedAt
                      ? new Date(row.redeemedAt).toLocaleString("vi-VN")
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!rows.length && (
          <p className={styles.empty}>
            Chưa có giao dịch trong phạm vi đã chọn.
          </p>
        )}
      </section>
    </div>
  );
}
