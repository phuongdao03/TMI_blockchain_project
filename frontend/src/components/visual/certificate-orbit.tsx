import {
  BadgeCheck,
  Check,
  FileBadge2,
  Fingerprint,
  Hash,
  Link2,
} from "lucide-react";

import { cn } from "@/lib/utils";

const evidenceSteps = [
  { label: "Nguồn dữ liệu", value: "Đã đối chiếu" },
  { label: "Thẩm định", value: "Đủ điều kiện" },
  { label: "Dấu thời gian", value: "Đã ghi nhận" },
] as const;

const previewSteps = [
  { label: "Khởi nguồn", value: "Giá trị được hình thành" },
  { label: "Dấu ấn", value: "Câu chuyện được tiếp nối" },
  { label: "Lan tỏa", value: "Đến gần hơn với cộng đồng" },
] as const;

export function CertificateOrbit({
  className,
  preview = false,
}: {
  className?: string;
  preview?: boolean;
}) {
  const steps = preview ? previewSteps : evidenceSteps;
  return (
    <figure
      aria-label="Hồ sơ đề cử minh họa"
      className={cn("evidence-register", className)}
      role="img"
    >
      <div aria-hidden="true" className="evidence-register-frame">
        <div className="evidence-register-index">
          <span>ĐỀ CỬ</span>
          <strong>01</strong>
          <span>TMI / 26</span>
        </div>
        <div className="evidence-document">
          <div className="evidence-document-head">
            <span className="evidence-document-icon">
              <FileBadge2 className="size-6" strokeWidth={1.6} />
            </span>
            <span>
              <small>
                {preview ? "HÀNH TRÌNH GIÁ TRỊ VIỆT" : "SỔ ĐĂNG BỘ SỐ"}
              </small>
              <strong>
                {preview ? "DẤU ẤN TINH HOA VIỆT" : "TINH HOA VIỆT"}
              </strong>
            </span>
            <BadgeCheck
              className="ml-auto size-6 text-gold-300"
              strokeWidth={1.7}
            />
          </div>
          <div className="evidence-document-code">
            <span>{preview ? "MÃ CHUYÊN ĐỀ" : "MÃ BẰNG CHỨNG"}</span>
            <strong>{preview ? "THV–GT–2026–001" : "THV–VN–2026–0812"}</strong>
          </div>
          <dl className="evidence-document-fields">
            <div>
              <dt>{preview ? "Giá trị" : "Chủ thể"}</dt>
              <dd>{preview ? "Nét đẹp tiêu biểu" : "Đề cử Tinh Hoa Việt"}</dd>
            </div>
            <div>
              <dt>{preview ? "Góc nhìn" : "Phiên bản"}</dt>
              <dd>{preview ? "Câu chuyện Việt" : "01 · Bất biến"}</dd>
            </div>
            <div>
              <dt>Trạng thái</dt>
              <dd className="evidence-valid">
                {preview ? null : <Check className="size-3.5" />}
                {preview ? "Đang giới thiệu" : "Đã xác lập"}
              </dd>
            </div>
          </dl>
          <div className="evidence-fingerprint">
            <Fingerprint
              className="size-8 text-primary-500"
              strokeWidth={1.4}
            />
            <span>
              <small>
                {preview ? "CÂU CHUYỆN NỔI BẬT" : "DẤU VÂN TAY DỮ LIỆU"}
              </small>
              <strong>
                {preview
                  ? "GIÁ TRỊ ĐƯỢC GÌN GIỮ VÀ LAN TỎA"
                  : "7F4A · 8C29 · B15E · 03D1"}
              </strong>
            </span>
          </div>
        </div>
        <div className="evidence-chain">
          <div className="evidence-chain-head">
            <span>
              <Link2 className="size-4" />
              {preview ? " HÀNH TRÌNH KHÁM PHÁ" : " CHUỖI ĐỐI CHIẾU"}
            </span>
            <Hash className="size-4 text-slate-600" />
          </div>
          <ol>
            {steps.map((step, index) => (
              <li key={step.label}>
                <span className="evidence-chain-number">0{index + 1}</span>
                <span>
                  <small>{step.label}</small>
                  <strong>{step.value}</strong>
                </span>
                {preview ? null : (
                  <Check className="ml-auto size-4 text-emerald-400" />
                )}
              </li>
            ))}
          </ol>
        </div>
        <div className="evidence-seal">
          <BadgeCheck className="size-5" />
          <span>
            <small>
              {preview ? "NỘI DUNG TIÊU BIỂU" : "THÔNG TIN CÔNG KHAI"}
            </small>
            <strong>{preview ? "Tinh hoa Việt" : "Sẵn sàng xác minh"}</strong>
          </span>
        </div>
      </div>
    </figure>
  );
}
