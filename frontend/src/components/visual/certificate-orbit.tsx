import { FileText, Hash, Layers3, Link2 } from "lucide-react";

import { cn } from "@/lib/utils";

const informationSteps = [
  { label: "Tiếp nhận", value: "Thông tin hồ sơ và tài liệu" },
  { label: "Thẩm định", value: "Kết quả xử lý và yêu cầu bổ sung" },
  { label: "Công bố", value: "Nội dung được phép hiển thị" },
] as const;

/**
 * A decorative explanation of the public-information flow. It deliberately
 * contains no certificate number, transaction hash, or verification state so
 * the landing page never presents a fabricated record as a real one.
 */
export function CertificateOrbit({ className }: { className?: string }) {
  return (
    <figure
      aria-label="Sơ đồ phạm vi thông tin công bố trên nền tảng Tinh Hoa Việt"
      className={cn("evidence-register", className)}
      role="img"
    >
      <div aria-hidden="true" className="evidence-register-frame">
        <div className="evidence-register-index">
          <span>THV</span>
          <strong>∞</strong>
          <span>GIỚI THIỆU</span>
        </div>
        <div className="evidence-document">
          <div className="evidence-document-head">
            <span className="evidence-document-icon">
              <FileText className="size-6" strokeWidth={1.6} />
            </span>
            <span>
              <small>KHÔNG GIAN THÔNG TIN</small>
              <strong>ĐỀ CỬ TINH HOA VIỆT</strong>
            </span>
            <Layers3
              className="ml-auto size-6 text-gold-300"
              strokeWidth={1.7}
            />
          </div>
          <div className="evidence-document-code">
            <span>HỒ SƠ ĐƯỢC CÔNG BỐ</span>
            <strong>Thông tin đã được phê duyệt</strong>
          </div>
          <dl className="evidence-document-fields">
            <div>
              <dt>Nội dung công bố</dt>
              <dd>Đề cử &amp; giới thiệu</dd>
            </div>
            <div>
              <dt>Kiểm chứng</dt>
              <dd>Mã tra cứu</dd>
            </div>
            <div>
              <dt>Trạng thái hồ sơ</dt>
              <dd>Quyết định xử lý</dd>
            </div>
          </dl>
          <div className="evidence-fingerprint">
            <Layers3 className="size-8 text-primary-500" strokeWidth={1.4} />
            <span>
              <small>HÀNH TRÌNH HỒ SƠ</small>
              <strong>Các mốc xử lý được cập nhật theo quy trình</strong>
            </span>
          </div>
        </div>
        <div className="evidence-chain">
          <div className="evidence-chain-head">
            <span>
              <Link2 className="size-4" /> QUY TRÌNH XỬ LÝ
            </span>
            <Hash className="size-4 text-slate-600" />
          </div>
          <ol>
            {informationSteps.map((step, index) => (
              <li key={step.label}>
                <span className="evidence-chain-number">0{index + 1}</span>
                <span>
                  <small>{step.label}</small>
                  <strong>{step.value}</strong>
                </span>
              </li>
            ))}
          </ol>
        </div>
        <div className="evidence-seal">
          <FileText className="size-5" />
          <span>
            <small>PHẠM VI HIỂN THỊ</small>
            <strong>THÔNG TIN CÔNG BỐ</strong>
          </span>
        </div>
      </div>
    </figure>
  );
}
