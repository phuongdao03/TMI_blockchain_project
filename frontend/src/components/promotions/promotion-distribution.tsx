"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { promotionApi } from "@/lib/api/client";
import type { AudiencePreview } from "@/lib/api/promotion-types";
import { formatVnd } from "@/lib/wallet/summary";
import { Choice, Field, readableError } from "./form-fields";
import styles from "./promotions.module.css";

export function parseRecipientList(value: string) {
  const tokens = value
    .replace(/"/g, "")
    .split(/[\s,;]+/)
    .filter(Boolean)
    .filter((token) => !/[a-z_]*user_?id[s]?$/i.test(token));
  const valid = tokens.filter((token) =>
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      token,
    ),
  );
  return {
    userIds: [...new Set(valid)],
    duplicates: valid.length - new Set(valid).size,
    invalid: tokens.filter((token) => !valid.includes(token)),
  };
}
export function PromotionDistribution({ initialId }: { initialId?: string }) {
  const client = useQueryClient();
  const campaigns = useQuery({
    queryKey: ["promotions", "select"],
    queryFn: () => promotionApi.list("pageSize=100"),
  });
  const [id, setId] = useState(initialId ?? "");
  const [text, setText] = useState("");
  const [reason, setReason] = useState("");
  const [search, setSearch] = useState("");
  const searchUsers = useMutation({
    mutationFn: () => promotionApi.searchRecipients(id, search.trim()),
  });
  const [preview, setPreview] = useState<AudiencePreview | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [key, setKey] = useState("");
  const parsed = parseRecipientList(text);
  const jobs = useQuery({
    queryKey: ["promotions", "jobs", id],
    queryFn: () => promotionApi.jobs(id),
    enabled: Boolean(id),
    refetchInterval: (query) =>
      query.state.data?.items.some((job) =>
        ["PENDING", "RUNNING"].includes(job.status),
      )
        ? 3000
        : false,
  });
  const audience = useMutation({
    mutationFn: () =>
      promotionApi.audience(id, text.trim() ? parsed.userIds : undefined),
    onSuccess: (data) => {
      setPreview(data);
      setKey(crypto.randomUUID());
    },
  });
  const issue = useMutation({
    mutationFn: () =>
      promotionApi.issue(id, {
        userIds: text.trim() ? parsed.userIds : undefined,
        reason,
        idempotencyKey: key,
        previewToken: preview!.previewToken,
      }),
    onSuccess: async () => {
      setConfirmed(false);
      setPreview(null);
      await client.invalidateQueries({ queryKey: ["promotions"] });
    },
  });
  function reset() {
    setPreview(null);
    setConfirmed(false);
  }
  return (
    <div className={styles.two}>
      <section className={`${styles.panel} ${styles.stack}`}>
        <h2>Chọn đối tượng & phát voucher</h2>
        <Choice
          label="Chiến dịch"
          value={id}
          onChange={(e) => {
            setId(e.target.value);
            reset();
          }}
        >
          <option value="">Chọn chiến dịch</option>
          {campaigns.data?.items.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} · {c.status}
            </option>
          ))}
        </Choice>
        <p className={styles.muted}>
          Để trống danh sách để dùng bộ điều kiện đã lưu của chiến dịch. Nhân
          viên và tài khoản nội bộ luôn bị loại.
        </p>
        <Field label="Tìm khách hàng theo email hoặc ID">
          <div className="flex gap-2">
            <input
              value={search}
              maxLength={120}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Button
              disabled={
                !id || search.trim().length < 2 || searchUsers.isPending
              }
              onClick={() => searchUsers.mutate()}
            >
              Tìm
            </Button>
          </div>
        </Field>
        {searchUsers.isError && (
          <p role="alert">{readableError(searchUsers.error)}</p>
        )}
        {searchUsers.data && (
          <ul className="space-y-2 text-sm">
            {searchUsers.data.items.map((user) => (
              <li
                key={user.id}
                className="flex items-center justify-between gap-2"
              >
                <span>
                  {user.email} · {user.eligible ? "Đủ điều kiện" : user.reason}
                </span>
                <Button
                  disabled={!user.eligible || parsed.userIds.includes(user.id)}
                  onClick={() => {
                    setText((previous) => `${previous}\n${user.id}`.trim());
                    reset();
                  }}
                >
                  Thêm
                </Button>
              </li>
            ))}
            {!searchUsers.data.items.length && (
              <li>Không tìm thấy tài khoản phù hợp.</li>
            )}
          </ul>
        )}
        <Field label="Danh sách người nhận (mỗi dòng một UUID)">
          <textarea
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              reset();
            }}
            placeholder="Dán danh sách ID hoặc chọn CSV bên dưới"
          />
        </Field>
        <label className={styles.field}>
          <span>Nhập CSV danh sách ID</span>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (file) {
                setText(await file.text());
                reset();
              }
            }}
          />
        </label>
        {text && (
          <p className={styles.muted}>
            {parsed.userIds.length} ID hợp lệ · {parsed.duplicates} trùng ·{" "}
            {parsed.invalid.length} sai định dạng
          </p>
        )}
        {parsed.invalid.length > 0 && (
          <p role="alert" className={styles.error}>
            Hãy sửa các ID không hợp lệ: {parsed.invalid.slice(0, 5).join(", ")}
          </p>
        )}
        <Field label="Lý do cấp / ghi chú thao tác">
          <textarea
            value={reason}
            minLength={5}
            maxLength={255}
            onChange={(e) => setReason(e.target.value)}
          />
        </Field>
        <Button
          variant="outline"
          disabled={!id || audience.isPending || parsed.invalid.length > 0}
          onClick={() => audience.mutate()}
        >
          {audience.isPending ? "Đang kiểm tra…" : "Xem trước đối tượng"}
        </Button>
        {(audience.isError || issue.isError) && (
          <p role="alert" className={styles.error}>
            {readableError(audience.error ?? issue.error)}
          </p>
        )}
        {preview && (
          <div className={styles.stack}>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <dt>Đủ điều kiện</dt>
              <dd>{preview.eligibleCount}</dd>
              <dt>Bị loại</dt>
              <dd>{preview.excludedCount}</dd>
              <dt>Giá trị danh nghĩa</dt>
              <dd>{formatVnd(preview.nominalValueVnd)}</dd>
            </dl>
            <p className={styles.muted}>
              Giá trị danh nghĩa không phải ngân sách đã chi. Đối tượng được
              kiểm tra lại tại backend trước khi cấp.
            </p>
            <ul className="space-y-1 text-sm">
              {Object.entries(preview.exclusionReasons).map(
                ([label, count]) => (
                  <li key={label}>
                    {label}: {count}
                  </li>
                ),
              )}
            </ul>
            <div className={styles.table}>
              <table>
                <thead>
                  <tr>
                    <th>Tài khoản mẫu</th>
                    <th>Kết quả</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.sample.map((user) => (
                    <tr key={user.id}>
                      <td>{user.email || user.id}</td>
                      <td>{user.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Button
              disabled={!preview.eligibleCount || reason.trim().length < 5}
              onClick={() => setConfirmed(true)}
            >
              Xác nhận phát voucher
            </Button>
          </div>
        )}
      </section>
      <section className={`${styles.panel} ${styles.stack}`}>
        <h2>Tiến độ phân phối</h2>
        {jobs.isPending && id && <p role="status">Đang tải tiến độ…</p>}
        {jobs.data?.items.length === 0 && (
          <p className={styles.empty}>Chưa có đợt phân phối.</p>
        )}
        {jobs.data?.items.map((job) => (
          <article key={job.id} className={styles.panel}>
            <p className="font-semibold">{job.status}</p>
            <progress
              className="my-3 w-full"
              value={job.processed}
              max={Math.max(1, job.total)}
              aria-label="Tiến độ phát voucher"
            />
            <p className={styles.muted}>
              {job.processed}/{job.total} đã xử lý · {job.issued} đã cấp ·{" "}
              {job.failed} lỗi
            </p>
            {job.errors?.map((error, index) => (
              <p className={styles.error} key={`${error.userId}-${index}`}>
                {error.userId}: {error.reason}
              </p>
            ))}
          </article>
        ))}
      </section>
      <ConfirmationDialog
        open={confirmed}
        title="Phát voucher cho danh sách đã xem trước?"
        description={`Dự kiến ${preview?.eligibleCount ?? 0} người đủ điều kiện. Backend sẽ kiểm tra lại và tránh cấp trùng kể cả khi thử lại.`}
        confirmLabel="Bắt đầu phân phối"
        isPending={issue.isPending}
        onCancel={() => setConfirmed(false)}
        onConfirm={() => issue.mutate()}
      />
    </div>
  );
}
