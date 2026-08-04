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
  { label: "Thẩm định 5T", value: "Đủ điều kiện" },
  { label: "Dấu thời gian", value: "Đã ghi nhận" },
] as const;

export function CertificateOrbit({ className }: { className?: string }) {
  return (
    <figure
      aria-label="Sổ bằng chứng số TMI"
      className={cn("evidence-register", className)}
      role="img"
    >
      <div aria-hidden="true" className="evidence-register-frame">
        <div className="evidence-register-index">
          <span>HỒ SƠ</span>
          <strong>01</strong>
          <span>TMI / 26</span>
        </div>

        <div className="evidence-document">
          <div className="evidence-document-head">
            <span className="evidence-document-icon">
              <FileBadge2 className="size-6" strokeWidth={1.6} />
            </span>
            <span>
              <small>SỔ ĐĂNG BỘ SỐ</small>
              <strong>TMI CERTIFICATE</strong>
            </span>
            <BadgeCheck
              className="ml-auto size-6 text-gold-300"
              strokeWidth={1.7}
            />
          </div>

          <div className="evidence-document-code">
            <span>MÃ BẰNG CHỨNG</span>
            <strong>TMI–VN–2026–0812</strong>
          </div>

          <dl className="evidence-document-fields">
            <div>
              <dt>Chủ thể</dt>
              <dd>TMI Digital Registry</dd>
            </div>
            <div>
              <dt>Phiên bản</dt>
              <dd>01 · Bất biến</dd>
            </div>
            <div>
              <dt>Trạng thái</dt>
              <dd className="evidence-valid">
                <Check className="size-3.5" /> Đã xác lập
              </dd>
            </div>
          </dl>

          <div className="evidence-fingerprint">
            <Fingerprint
              className="size-8 text-primary-500"
              strokeWidth={1.4}
            />
            <span>
              <small>DẤU VÂN TAY DỮ LIỆU</small>
              <strong>7F4A · 8C29 · B15E · 03D1</strong>
            </span>
          </div>
        </div>

        <div className="evidence-chain">
          <div className="evidence-chain-head">
            <span>
              <Link2 className="size-4" /> CHUỖI ĐỐI CHIẾU
            </span>
            <Hash className="size-4 text-slate-600" />
          </div>
          <ol>
            {evidenceSteps.map((step, index) => (
              <li key={step.label}>
                <span className="evidence-chain-number">0{index + 1}</span>
                <span>
                  <small>{step.label}</small>
                  <strong>{step.value}</strong>
                </span>
                <Check className="ml-auto size-4 text-emerald-400" />
              </li>
            ))}
          </ol>
        </div>

        <div className="evidence-seal">
          <BadgeCheck className="size-5" />
          <span>
            <small>PUBLIC PROOF</small>
            <strong>Sẵn sàng xác minh</strong>
          </span>
        </div>
      </div>
    </figure>
  );
}
