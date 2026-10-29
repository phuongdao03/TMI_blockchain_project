"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { promotionApi } from "@/lib/api/client";
import { useAuthUser } from "@/lib/auth/user-context";
import { CampaignBuilder } from "./campaign-builder";
import { PromotionCampaignList } from "./promotion-campaign-list";
import { PromotionDistribution } from "./promotion-distribution";
import { PromotionMediaLibrary } from "./promotion-media-library";
import { PromotionMetrics, PromotionReports } from "./promotion-reports";
import { readableError } from "./form-fields";
import styles from "./promotions.module.css";

const navigation = [
  ["", "Tổng quan"],
  ["campaigns", "Chiến dịch"],
  ["popups", "Thiết kế popup"],
  ["media", "Kho hình ảnh"],
  ["distribution", "Phân phối"],
  ["history", "Lịch sử sử dụng"],
  ["reports", "Báo cáo"],
  ["audit", "Nhật ký"],
  ["settings", "Cài đặt"],
] as const;
export function PromotionAdminWorkspace({
  section = [],
}: {
  section?: string[];
}) {
  const user = useAuthUser();
  const manage = Boolean(
    user?.roles.includes("SUPER_ADMIN") ||
      user?.permissions?.includes("promotions.manage"),
  );
  const read =
    manage || Boolean(user?.permissions?.includes("promotions.read"));
  if (!read)
    return (
      <p role="alert" className={styles.error}>
        Bạn chưa có quyền truy cập Marketing & Khuyến mại.
      </p>
    );
  return <PromotionAdminContent section={section} canManage={manage} />;
}
function PromotionAdminContent({
  section,
  canManage,
}: {
  section: string[];
  canManage: boolean;
}) {
  const pathname = usePathname();
  const query = useSearchParams();
  const [area, sub] = section;
  const initialId = query.get("campaign") ?? undefined;
  let content;
  if (area === "new" || sub === "edit" || sub === "popup")
    content = canManage ? (
      <CampaignBuilder
        id={area === "new" ? undefined : area}
        presentationOnly={sub === "popup"}
      />
    ) : (
      <p role="alert">Bạn cần quyền quản lý để chỉnh sửa chiến dịch.</p>
    );
  else if (area === "campaigns" || area === "popups")
    content = (
      <PromotionCampaignList
        canManage={canManage}
        popupOnly={area === "popups"}
      />
    );
  else if (area === "media")
    content = <PromotionMediaLibrary canManage={canManage} />;
  else if (area === "distribution")
    content = canManage ? (
      <PromotionDistribution initialId={initialId} />
    ) : (
      <p role="alert">Bạn cần quyền quản lý để phát voucher.</p>
    );
  else if (area === "reports" || area === "history")
    content = (
      <PromotionReports initialId={initialId} history={area === "history"} />
    );
  else if (area === "settings") content = <PromotionSettings />;
  else if (area === "audit") content = <PromotionAuditLog />;
  else content = <PromotionOverview />;
  return (
    <section className={styles.workspace}>
      <header className={styles.heading}>
        <div>
          <p className={styles.eyebrow}>Trung tâm ưu đãi</p>
          <h1>Marketing & Khuyến mại</h1>
          <p className={styles.muted}>
            Thiết kế, phân phối và theo dõi ưu đãi trên cùng một hệ thống.
          </p>
        </div>
        {canManage && (
          <Link className={styles.link} href="/admin/promotions/new">
            + Tạo chiến dịch
          </Link>
        )}
      </header>
      <nav aria-label="Khu vực quản lý khuyến mại" className={styles.nav}>
        {navigation.map(([path, label]) => (
          <Link
            key={path}
            href={`/admin/promotions${path ? `/${path}` : ""}`}
            aria-current={
              pathname === `/admin/promotions${path ? `/${path}` : ""}`
                ? "page"
                : undefined
            }
          >
            {label}
          </Link>
        ))}
      </nav>
      {content}
    </section>
  );
}
function PromotionOverview() {
  const stats = useQuery({
    queryKey: ["promotions", "analytics"],
    queryFn: () => promotionApi.stats(),
  });
  return (
    <div className={styles.stack}>
      {stats.isPending && <p role="status">Đang tải tổng quan…</p>}
      {stats.isError && (
        <p role="alert" className={styles.error}>
          {readableError(stats.error)}
        </p>
      )}
      {stats.data && <PromotionMetrics data={stats.data} />}
      <div className={styles.panel}>
        <h2>Bắt đầu một chương trình</h2>
        <p className={styles.muted}>
          Tạo chiến dịch → chọn đối tượng → xem trước → xuất bản → phân phối →
          theo dõi thanh toán. Chiến dịch tri ân thành viên sớm luôn cần ngày
          cutoff được Admin xác nhận.
        </p>
        <div className={`${styles.actions} mt-4`}>
          <Link className={styles.link} href="/admin/promotions/campaigns">
            Mở danh sách chiến dịch
          </Link>
          <Link className={styles.link} href="/admin/promotions/distribution">
            Xem trước đối tượng
          </Link>
        </div>
      </div>
    </div>
  );
}
function PromotionSettings() {
  const settings = useQuery({
    queryKey: ["promotions", "settings"],
    queryFn: promotionApi.settings,
  });
  return (
    <section className={styles.panel}>
      <h2>Quy tắc nền tảng</h2>
      {settings.isPending && <p role="status">Đang tải cài đặt…</p>}
      {settings.isError && (
        <p role="alert" className={styles.error}>
          {readableError(settings.error)}
        </p>
      )}
      {settings.data && (
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <dt>Múi giờ hiển thị</dt>
          <dd>{settings.data.timezone}</dd>
          <dt>Dung lượng ảnh tối đa</dt>
          <dd>{Math.floor(settings.data.maxImageBytes / 1024 / 1024)} MB</dd>
          <dt>Role nhận ưu đãi</dt>
          <dd>{settings.data.eligibleRoles.join(", ")}</dd>
          <dt>Tài khoản nhân viên</dt>
          <dd>
            {settings.data.excludedEmployees
              ? "Luôn bị loại"
              : "Theo chính sách"}
          </dd>
        </dl>
      )}
      <p className={`${styles.muted} mt-6`}>
        Ngân sách, thời hạn, thông báo, tần suất popup và điều kiện được cấu
        hình riêng trong từng chiến dịch. Các giới hạn an toàn nền tảng do quản
        trị kỹ thuật kiểm soát.
      </p>
    </section>
  );
}
function PromotionAuditLog() {
  const audit = useQuery({
    queryKey: ["promotions", "audit"],
    queryFn: promotionApi.audit,
  });
  return (
    <section className={styles.panel}>
      <h2>Nhật ký thao tác</h2>
      {audit.isPending && <p role="status">Đang tải nhật ký…</p>}
      {audit.isError && (
        <p role="alert" className={styles.error}>
          {readableError(audit.error)}
        </p>
      )}
      <div className={styles.table}>
        <table>
          <thead>
            <tr>
              <th>Thao tác</th>
              <th>Người thực hiện</th>
              <th>Chiến dịch</th>
              <th>Thời điểm</th>
            </tr>
          </thead>
          <tbody>
            {audit.data?.items.map((row) => (
              <tr key={row.id}>
                <td>{row.action}</td>
                <td className="break-all">{row.actorUserId ?? "Hệ thống"}</td>
                <td className="break-all">{row.campaignId ?? "—"}</td>
                <td>{new Date(row.createdAt).toLocaleString("vi-VN")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {audit.data?.items.length === 0 && (
        <p className={styles.empty}>
          Chưa có thao tác trong hệ thống khuyến mại.
        </p>
      )}
    </section>
  );
}
