import Image from "next/image";
import { Download, FileText } from "lucide-react";

import { HeritageGallery } from "./heritage-gallery";
import { DeferredProposalViewer } from "./deferred-proposal-viewer";
import { WelcomeMusic } from "./welcome-music";

const decision = "/assets/institution/decision.pdf";
const proposal = "/assets/institution/proposal-2026.pdf";

export function InstitutionContent() {
  return (
    <>
      <section
        aria-labelledby="institution-title"
        className="institution-section"
        id="van-ban-thanh-lap"
      >
        <div className="institution-section__inner institution-decision">
          <div className="institution-decision__copy">
            <p className="institution-eyebrow">Văn bản thành lập</p>
            <h2 id="institution-title">
              Trung tâm Xác lập <span>Tinh Hoa Việt.</span>
            </h2>
            <p className="institution-lead">
              Quyết định số 55 ngày 02/01/2026 của Viện Những Vấn đề Phát triển
              (VIDS) thành lập Trung tâm Xác lập Tinh Hoa Việt. Văn bản gốc được
              công bố để người đọc trực tiếp đối chiếu thông tin về đơn vị ban
              hành và căn cứ thành lập.
            </p>
            <dl className="institution-facts">
              <div>
                <dt>Văn bản</dt>
                <dd>Quyết định số 55</dd>
              </div>
              <div>
                <dt>Ngày ban hành</dt>
                <dd>02/01/2026</dd>
              </div>
              <div>
                <dt>Đơn vị ban hành</dt>
                <dd>Viện Những Vấn đề Phát triển (VIDS)</dd>
              </div>
            </dl>
            <div className="institution-actions">
              <a
                className="institution-button institution-button--primary"
                href={decision}
                rel="noopener"
                target="_blank"
              >
                <FileText aria-hidden="true" size={18} /> Xem quyết định
              </a>
              <a className="institution-button" download href={decision}>
                <Download aria-hidden="true" size={18} /> Tải PDF · 2 trang
              </a>
            </div>
            <WelcomeMusic />
          </div>
          <a
            aria-label="Mở toàn bộ Quyết định thành lập Trung tâm Xác lập Tinh Hoa Việt"
            className="institution-decision__preview"
            href={decision}
            rel="noopener"
            target="_blank"
          >
            <Image
              alt="Trang đầu Quyết định số 55 về việc thành lập Trung tâm Xác lập Tinh Hoa Việt"
              height={982}
              sizes="(max-width: 48rem) 100vw, 30vw"
              src="/assets/institution/decision-preview.jpg"
              width={700}
            />
            <span>
              <FileText aria-hidden="true" size={17} /> Quyết định thành lập{" "}
              <small>PDF · 2 trang</small>
            </span>
          </a>
        </div>
      </section>

      <HeritageGallery />

      <section
        aria-labelledby="proposal-title"
        className="institution-section institution-section--proposal"
        id="ho-so-2026"
      >
        <div className="institution-section__inner">
          <div className="institution-section__heading">
            <div>
              <p className="institution-eyebrow">Hồ sơ trực tuyến · Kỳ 2026</p>
              <h2 id="proposal-title">
                Mở từng trang. <span>Hiểu trọn hành trình.</span>
              </h2>
            </div>
            <div className="institution-section__summary">
              <p>
                Proposal Lễ Công bố Đề cử và Xác lập Tinh Hoa Việt. Kế hoạch tổ
                chức, thông điệp và quyền lợi đồng hành trong 53 trang tài liệu.
              </p>
              <div className="institution-section__summary-actions">
                <span className="institution-document-badge">
                  53 trang · Bản cập nhật
                </span>
                <a className="institution-button" download href={proposal}>
                  <Download aria-hidden="true" size={18} /> Tải proposal PDF
                </a>
              </div>
            </div>
          </div>
          <DeferredProposalViewer />
        </div>
      </section>
    </>
  );
}
