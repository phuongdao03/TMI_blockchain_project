import Link from "next/link";
import type { DossierStatus } from "@/lib/api/types";

const approvedStatuses: DossierStatus[] = [
  "APPROVED",
  "PAID",
  "ANCHOR_PENDING",
  "ANCHORED",
  "CERTIFICATE_ISSUED",
  "PUBLISHED",
];

export function DossierPromotionOptions({
  dossierId,
  status,
}: {
  dossierId: string;
  status: DossierStatus;
}) {
  if (!approvedStatuses.includes(status)) return null;
  const published = status === "PUBLISHED";
  return (
    <section
      aria-labelledby="dossier-promotion-title"
      className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5"
    >
      <h2 id="dossier-promotion-title" className="text-lg font-bold">
        {published ? "Quảng bá sau công bố" : "Hồ sơ đã được phê duyệt"}
      </h2>
      <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
        {published
          ? "Bạn có thể mua thêm hoặc gia hạn quảng cáo; không cần nộp lại hồ sơ hay đóng lại phí nộp chỉ để quảng bá."
          : "Bạn có thể theo dõi công bố thông thường mà không mua quảng cáo, hoặc chọn gói quảng bá phù hợp. Hồ sơ vẫn cần hoàn tất các điều kiện công bố hiện hành."}
      </p>
      <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">
        Quảng cáo không phải điều kiện công bố. Quảng cáo chờ duyệt hoặc chờ
        thanh toán không chặn hồ sơ đã đủ điều kiện công bố.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {!published ? (
          <Link
            className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold"
            href="#dossier-publication-progress"
          >
            Theo dõi công bố thông thường
          </Link>
        ) : null}
        <Link
          className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold"
          href={`/advertising?dossierId=${encodeURIComponent(dossierId)}`}
        >
          {published ? "Quảng bá hồ sơ này" : "Chọn gói quảng bá"}
        </Link>
      </div>
    </section>
  );
}
