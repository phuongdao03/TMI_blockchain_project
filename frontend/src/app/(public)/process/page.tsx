import Link from "next/link";

import {
  AccessGuide,
  ProcessGuide,
} from "@/components/public/platform-guidance";
import { isPreviewRelease } from "@/lib/release-mode";

const publicJourney = [
  {
    number: "01",
    title: "Khám phá đề cử",
    detail:
      "Tìm hiểu những con người, tác phẩm và giá trị Việt đã được giới thiệu công khai.",
  },
  {
    number: "02",
    title: "Tìm hiểu câu chuyện",
    detail:
      "Xem nội dung, hình ảnh và thông tin nguồn được phép công bố cho từng đề cử.",
  },
  {
    number: "03",
    title: "Theo dõi chương trình",
    detail:
      "Đăng ký tài khoản để lưu hành trình và nhận thông báo khi các hoạt động mới được mở.",
  },
] as const;

export default function ProcessPage() {
  const preview = isPreviewRelease();

  if (preview) {
    return (
      <div className="process-page">
        <header className="public-page-header">
          <div className="public-page-header__content">
            <p>CÁCH CHƯƠNG TRÌNH HOẠT ĐỘNG</p>
            <h1>Hành trình từ một đề cử đến giá trị được lan tỏa.</h1>
            <p>
              Hiện tại, chương trình tập trung giúp cộng đồng khám phá nội dung
              đã được công bố. Hoạt động gửi hồ sơ được mở theo từng giai đoạn.
            </p>
          </div>
        </header>

        <section className="public-preview-journey">
          <ol>
            {publicJourney.map((step) => (
              <li key={step.number}>
                <span>{step.number}</span>
                <h2>{step.title}</h2>
                <p>{step.detail}</p>
              </li>
            ))}
          </ol>
          <aside>
            <div>
              <p>GIAI ĐOẠN TIẾP THEO</p>
              <h2>Cổng gửi đề cử sắp ra mắt</h2>
              <p>
                Khi được mở, người tham gia sẽ có thể chuẩn bị thông tin, gửi đề
                cử và theo dõi tiến trình ngay trong tài khoản của mình.
              </p>
            </div>
            <Link href="/coming-soon/submission">Xem thông tin mở cổng</Link>
          </aside>
        </section>
      </div>
    );
  }

  return (
    <div className="process-page">
      <header className="public-page-header">
        <div className="public-page-header__content public-page-header__content--split">
          <div>
            <p>HÀNH TRÌNH GỬI HỒ SƠ</p>
            <h1>Hành trình hồ sơ, rõ ràng từ đầu đến cuối.</h1>
            <p>
              Chuẩn bị thông tin, gửi hồ sơ, theo dõi phản hồi và tra cứu kết
              quả trong một quy trình dễ theo dõi.
            </p>
          </div>
          <div className="public-page-header__action">
            <p>Sẵn sàng bắt đầu?</p>
            <Link href="/register">Tạo hồ sơ mới</Link>
          </div>
        </div>
      </header>
      <ProcessGuide />
      <AccessGuide />
    </div>
  );
}
