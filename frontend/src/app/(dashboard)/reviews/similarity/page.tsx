import { ArrowLeftRight } from "lucide-react";

import { RoleGate } from "@/components/auth/role-gate";
import { SimilarityReviewWorkspace } from "@/components/reviews/similarity-review-workspace";

export default function SimilarityReviewPage() {
  return (
    <RoleGate allowed={["REVIEWER"]}>
      <div className="mx-auto max-w-7xl space-y-7">
        <header className="border-b border-neutral-200 pb-7">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-primary-700">
            <ArrowLeftRight aria-hidden="true" className="size-4" />
            Công việc cần xử lý
          </p>
          <h1 className="mt-3 text-3xl font-bold tracking-[-0.03em] sm:text-4xl">
            Đối chiếu nội dung tương đồng
          </h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
            So sánh từng cặp hồ sơ được giao, ghi nhận căn cứ và đưa ra kết luận
            độc lập. Tín hiệu hệ thống chỉ hỗ trợ sàng lọc, không thay thế đánh
            giá chuyên môn.
          </p>
        </header>
        <SimilarityReviewWorkspace />
      </div>
    </RoleGate>
  );
}
