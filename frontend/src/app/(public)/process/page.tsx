import Link from "next/link";
import { ArrowRight, Search } from "lucide-react";

import { ProcessJourney } from "@/components/public/process-journey";
import { isPreviewRelease } from "@/lib/release-mode";

function ProcessHeroArtwork() {
  return (
    <svg
      aria-hidden="true"
      className="process-hero__artwork"
      fill="none"
      viewBox="0 0 480 360"
    >
      <circle className="process-hero__ring" cx="240" cy="180" r="128" />
      <circle className="process-hero__ring" cx="240" cy="180" r="108" />
      <circle
        className="process-hero__ring process-hero__ring--fine"
        cx="240"
        cy="180"
        r="90"
      />
      <path className="process-hero__route" d="M112 180h79l41-48 47 48h89" />
      <path
        className="process-hero__route process-hero__route--vertical"
        d="M191 180v68m88-68v68"
      />
      <circle className="process-hero__step-dot" cx="112" cy="180" r="8" />
      <circle className="process-hero__step-dot" cx="191" cy="180" r="8" />
      <circle className="process-hero__step-dot" cx="279" cy="180" r="8" />
      <circle className="process-hero__step-dot" cx="368" cy="180" r="8" />
      <path className="process-hero__document" d="M174 94h57l24 24v38h-81z" />
      <path
        className="process-hero__document-line"
        d="M188 112h27m-27 12h46m-46 12h36"
      />
      <path className="process-hero__seal" d="m269 228 10 10 20-22" />
      <circle className="process-hero__seal-ring" cx="279" cy="228" r="25" />
      <circle className="process-hero__ornament" cx="240" cy="180" r="145" />
      <circle className="process-hero__ornament" cx="240" cy="180" r="154" />
    </svg>
  );
}

function ProcessActions({ submissionOpen }: { submissionOpen: boolean }) {
  return (
    <section aria-labelledby="process-next-title" className="process-next">
      <div className="process-next__inner">
        <div>
          <p className="public-information-kicker">BƯỚC TIẾP THEO</p>
          <h2 id="process-next-title">Bạn muốn bắt đầu từ đâu?</h2>
          <p>
            {submissionOpen
              ? "Tạo hồ sơ để bắt đầu, hoặc tra cứu thông tin đã được công bố."
              : "Tìm hiểu thông tin mở cổng, hoặc tra cứu bằng xác lập đã được công bố."}
          </p>
        </div>
        <div className="process-next__actions">
          {submissionOpen ? (
            <Link className="process-next__primary" href="/dossiers/new">
              Bắt đầu gửi hồ sơ
            </Link>
          ) : (
            <Link
              className="process-next__primary"
              href="/coming-soon/submission"
            >
              Xem thông tin mở cổng
            </Link>
          )}
          <Link className="process-next__secondary" href="/verify">
            Tra cứu kết quả
          </Link>
        </div>
      </div>
    </section>
  );
}

export default function ProcessPage() {
  const preview = isPreviewRelease();

  return (
    <div className={`process-page${preview ? " process-page--preview" : ""}`}>
      <header className="public-page-header process-hero">
        <div className="process-hero__inner">
          <div className="process-hero__copy">
            <p className="public-information-kicker">
              HƯỚNG DẪN GỬI HỒ SƠ ĐỀ CỬ
            </p>
            <h1>Hành trình đề cử Tinh Hoa Việt</h1>
            <p className="process-hero__description">
              Tìm hiểu cách chuẩn bị, gửi và theo dõi hồ sơ của bạn qua 4 bước
              đơn giản. Gửi đề cử không đồng nghĩa với việc chắc chắn được xác
              lập.
            </p>
            <div className="process-hero__actions">
              {preview ? (
                <Link
                  className="process-hero__primary"
                  href="/coming-soon/submission"
                >
                  Xem thông tin mở cổng
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Link>
              ) : (
                <Link className="process-hero__primary" href="/dossiers/new">
                  Bắt đầu gửi hồ sơ
                  <ArrowRight aria-hidden="true" className="size-4" />
                </Link>
              )}
              <Link className="process-hero__secondary" href="/verify">
                <Search aria-hidden="true" className="size-4" />
                Tra cứu kết quả
              </Link>
            </div>
            {preview ? (
              <p className="process-hero__availability">
                Cổng gửi hồ sơ được mở theo từng giai đoạn.
              </p>
            ) : null}
          </div>
          <div className="process-hero__visual">
            <ProcessHeroArtwork />
            <span aria-hidden="true" className="process-hero__caption">
              TỪ HỒ SƠ ĐẾN GIÁ TRỊ ĐƯỢC LAN TỎA
            </span>
          </div>
        </div>
      </header>
      <ProcessJourney submissionOpen={!preview} />
      <ProcessActions submissionOpen={!preview} />
    </div>
  );
}
