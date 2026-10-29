"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { promotionApi } from "@/lib/api/client";
import type { PromotionCampaign } from "@/lib/api/promotion-types";
import { Choice, readableError, TextField } from "./form-fields";
import styles from "./promotions.module.css";

const statuses: Record<string, string> = {
  DRAFT: "Nháp",
  SCHEDULED: "Đã đặt lịch",
  ACTIVE: "Đang chạy",
  PAUSED: "Tạm dừng",
  ENDED: "Đã kết thúc",
  ARCHIVED: "Lưu trữ",
};
export function PromotionCampaignList({
  canManage,
  popupOnly = false,
}: {
  canManage: boolean;
  popupOnly?: boolean;
}) {
  const router = useRouter();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("created_desc");
  const [page, setPage] = useState(1);
  const [action, setAction] = useState<{
    campaign: PromotionCampaign;
    action: "publish" | "pause" | "end" | "archive";
  } | null>(null);
  const params = new URLSearchParams({
    page: String(page),
    pageSize: "20",
    sort,
  });
  if (search) params.set("search", search);
  if (status) params.set("status", status);
  const campaigns = useQuery({
    queryKey: ["promotions", "list", params.toString()],
    queryFn: () => promotionApi.list(params.toString()),
  });
  const transition = useMutation({
    mutationFn: () =>
      promotionApi.transition(action!.campaign.id, action!.action),
    onSuccess: async () => {
      setAction(null);
      await client.invalidateQueries({ queryKey: ["promotions"] });
    },
  });
  const copy = useMutation({
    mutationFn: (id: string) => promotionApi.transition(id, "copy"),
    onSuccess: (campaign) => {
      void client.invalidateQueries({ queryKey: ["promotions"] });
      router.push(`/admin/promotions/${campaign.id}/edit`);
    },
  });
  return (
    <div className={styles.stack}>
      <div className={styles.grid}>
        <TextField
          label="Tìm chiến dịch"
          type="search"
          value={search}
          placeholder="Tên hoặc mã chiến dịch"
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <Choice
          label="Trạng thái"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Tất cả</option>
          {Object.entries(statuses).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </Choice>
        <Choice
          label="Sắp xếp"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="created_desc">Mới nhất</option>
          <option value="created_asc">Cũ nhất</option>
          <option value="name">Tên chiến dịch</option>
        </Choice>
      </div>
      {campaigns.isPending && <p role="status">Đang tải chiến dịch…</p>}
      {campaigns.isError && (
        <p role="alert" className={styles.error}>
          {readableError(campaigns.error)}
        </p>
      )}
      {copy.isError && (
        <p role="alert" className={styles.error}>
          {readableError(copy.error)}
        </p>
      )}
      <div className={`${styles.table} ${styles.campaignTable}`}>
        <table>
          <thead>
            <tr>
              <th>Chiến dịch</th>
              <th>Loại / đối tượng</th>
              <th>Thời gian</th>
              <th>Trạng thái</th>
              <th>Ngân sách đã dùng</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.data?.items.map((campaign) => (
              <tr key={campaign.id}>
                <td>
                  <Link
                    className="font-semibold hover:underline"
                    href={`/admin/promotions/${campaign.id}/edit`}
                  >
                    {campaign.name}
                  </Link>
                  <p className={styles.muted}>{campaign.code}</p>
                </td>
                <td>
                  {campaign.policy.discountType === "PERCENT"
                    ? `${campaign.policy.percentageBps / 100}%`
                    : `${campaign.amountVnd.toLocaleString("vi-VN")}đ`}
                  <p className={styles.muted}>{campaign.programType} · USER</p>
                </td>
                <td>
                  <p>
                    {campaign.startsAt
                      ? new Date(campaign.startsAt).toLocaleString("vi-VN")
                      : "Khi xuất bản"}
                  </p>
                  <p className={styles.muted}>
                    {campaign.endsAt
                      ? new Date(campaign.endsAt).toLocaleString("vi-VN")
                      : "Không đặt ngày kết thúc"}
                  </p>
                </td>
                <td>
                  <span className={styles.status}>
                    {statuses[campaign.status] ?? campaign.status}
                  </span>
                </td>
                <td>
                  {campaign.budgetSpentVnd.toLocaleString("vi-VN")}đ
                  <p className={styles.muted}>
                    Đang giữ:{" "}
                    {campaign.budgetReservedVnd.toLocaleString("vi-VN")}đ
                  </p>
                </td>
                <td>
                  <div className={styles.actions}>
                    <Link
                      className={styles.link}
                      href={`/admin/promotions/${campaign.id}/${popupOnly ? "popup" : "edit"}`}
                    >
                      {popupOnly ? "Thiết kế popup" : "Mở chiến dịch"}
                    </Link>
                    <Link
                      className={styles.link}
                      href={`/admin/promotions/distribution?campaign=${campaign.id}`}
                    >
                      Phân phối
                    </Link>
                    <Link
                      className={styles.link}
                      href={`/admin/promotions/reports?campaign=${campaign.id}`}
                    >
                      Báo cáo
                    </Link>
                    {canManage && (
                      <>
                        <Button
                          variant="ghost"
                          disabled={copy.isPending}
                          onClick={() => copy.mutate(campaign.id)}
                        >
                          Sao chép
                        </Button>
                        {["DRAFT", "PAUSED", "SCHEDULED"].includes(
                          campaign.status,
                        ) && (
                          <Button
                            variant="outline"
                            onClick={() =>
                              setAction({ campaign, action: "publish" })
                            }
                          >
                            Xuất bản
                          </Button>
                        )}
                        {campaign.status === "ACTIVE" && (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              setAction({ campaign, action: "pause" })
                            }
                          >
                            Tạm dừng
                          </Button>
                        )}
                        {!["ENDED", "ARCHIVED"].includes(campaign.status) && (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              setAction({ campaign, action: "end" })
                            }
                          >
                            Kết thúc
                          </Button>
                        )}
                        {campaign.status !== "ARCHIVED" && (
                          <Button
                            variant="ghost"
                            onClick={() =>
                              setAction({ campaign, action: "archive" })
                            }
                          >
                            Lưu trữ
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {campaigns.data?.total === 0 && (
        <p className={styles.empty}>
          Chưa có chiến dịch phù hợp. Tạo chiến dịch mới hoặc thay bộ lọc.
        </p>
      )}
      <div className={styles.actions}>
        <Button
          variant="outline"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          Trang trước
        </Button>
        <span className={styles.muted}>
          Trang {page} · {campaigns.data?.total ?? 0} chiến dịch
        </span>
        <Button
          variant="outline"
          disabled={!campaigns.data || page * 20 >= campaigns.data.total}
          onClick={() => setPage(page + 1)}
        >
          Trang sau
        </Button>
      </div>
      <ConfirmationDialog
        open={Boolean(action)}
        title={`${action?.action === "publish" ? "Xuất bản" : action?.action === "pause" ? "Tạm dừng" : action?.action === "end" ? "Kết thúc" : "Lưu trữ"} chiến dịch?`}
        description={
          action?.action === "publish"
            ? "Kiểm tra đối tượng, thời gian, ngân sách và nội dung trước khi xuất bản. Backend sẽ kiểm tra toàn bộ điều kiện; đối tượng chỉ gồm khách hàng hợp lệ."
            : "Lịch sử voucher và giao dịch đã phát sinh được giữ nguyên. Chính sách quyền lợi đã cam kết vẫn được áp dụng."
        }
        confirmLabel="Xác nhận"
        isPending={transition.isPending}
        onCancel={() => setAction(null)}
        onConfirm={() => transition.mutate()}
      >
        {transition.isError && (
          <p role="alert" className={styles.error}>
            {readableError(transition.error)}
          </p>
        )}
      </ConfirmationDialog>
    </div>
  );
}
