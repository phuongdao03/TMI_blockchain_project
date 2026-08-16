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
  { label: "Tuyển chọn", value: "Đang trưng bày" },
  { label: "Thông tin", value: "Đang cập nhật" },
  { label: "Chứng thư", value: "Chưa phát hành" },
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
              <small>{preview ? "BỘ SƯU TẬP MỞ ĐẦU" : "SỔ ĐĂNG BỘ SỐ"}</small>
              <strong>TINH HOA VIỆT</strong>
            </span>
            <BadgeCheck
              className="ml-auto size-6 text-gold-300"
              strokeWidth={1.7}
            />
          </div>
          <div className="evidence-document-code">
            <span>{preview ? "MÃ NỘI DUNG" : "MÃ BẰNG CHỨNG"}</span>
            <strong>{preview ? "THV–DECU–001" : "THV–VN–2026–0812"}</strong>
          </div>
          <dl className="evidence-document-fields">
            <div>
              <dt>Chủ thể</dt>
              <dd>
                {preview ? "Bộ sưu tập giới thiệu" : "Đề cử Tinh Hoa Việt"}
              </dd>
            </div>
            <div>
              <dt>Phiên bản</dt>
              <dd>{preview ? "Bản giới thiệu" : "01 · Bất biến"}</dd>
            </div>
            <div>
              <dt>Trạng thái</dt>
              <dd className="evidence-valid">
                {preview ? null : <Check className="size-3.5" />}
                {preview ? "Chưa phát hành" : "Đã xác lập"}
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
                {preview ? "THÔNG TIN TRƯNG BÀY" : "DẤU VÂN TAY DỮ LIỆU"}
              </small>
              <strong>
                {preview ? "NỘI DUNG GIỚI THIỆU" : "7F4A · 8C29 · B15E · 03D1"}
              </strong>
            </span>
          </div>
        </div>
        <div className="evidence-chain">
          <div className="evidence-chain-head">
            <span>
              <Link2 className="size-4" />
              {preview ? " LỘ TRÌNH PHÁT HÀNH" : " CHUỖI ĐỐI CHIẾU"}
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
              {preview ? "NỘI DUNG GIỚI THIỆU" : "THÔNG TIN CÔNG KHAI"}
            </small>
            <strong>
              {preview ? "Nội dung giới thiệu" : "Sẵn sàng xác minh"}
            </strong>
          </span>
        </div>
      </div>
    </figure>
  );
}
