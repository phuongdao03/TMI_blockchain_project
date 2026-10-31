import { HeritageGallery } from "./heritage-gallery";
import { DeferredProposalViewer } from "./deferred-proposal-viewer";
import { InstitutionDocumentPreview } from "./institution-document-preview";
import { WelcomeMusic } from "./welcome-music";
import proposalPages from "./proposal-page-text.json";

export function InstitutionContent() {
  return (
    <>
      <section
        aria-labelledby="institution-title"
        className="institution-section"
        id="van-ban-thanh-lap"
      >
        <div className="institution-section__inner institution-decision">
          <header className="institution-decision__heading">
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
          </header>
          <InstitutionDocumentPreview />
          <div className="institution-decision__details">
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
            <WelcomeMusic />
          </div>
        </div>
      </section>
      <HeritageGallery />
    </>
  );
}

export function ProposalSection() {
  return (
    <section
      aria-labelledby="proposal-title"
      className="institution-section institution-section--proposal"
      id="ho-so-2026"
    >
      <div className="institution-section__inner proposal-introduction">
        <div>
          <p className="institution-eyebrow">Tài liệu giới thiệu · Kỳ 2026</p>
          <h2 id="proposal-title">
            Mở từng trang. <span>Hiểu trọn hành trình.</span>
          </h2>
          <p className="institution-lead">
            Proposal Lễ Công bố Đề cử và Xác lập Tinh Hoa Việt. Kế hoạch tổ
            chức, thông điệp và quyền lợi đồng hành trong {proposalPages.length}{" "}
            trang tài liệu.
          </p>
          <p className="proposal-introduction__pages">
            {proposalPages.length} trang · Bản cập nhật
          </p>
          <p className="institution-lead">
            Đọc ngay bên dưới, chuyển trang hoặc mở toàn màn hình để xem rõ hơn.
          </p>
        </div>
        <DeferredProposalViewer />
        <a
          className="proposal-download"
          download
          href="/assets/institution/proposal-2026.pdf"
        >
          Tải bản PDF để lưu hoặc chia sẻ
        </a>
      </div>
    </section>
  );
}
