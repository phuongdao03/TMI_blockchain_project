import {
  Bell,
  BookOpen,
  CheckCircle2,
  CircleHelp,
  CreditCard,
  FileCheck2,
  FileText,
  QrCode,
  Search,
  ShieldCheck,
  UserRound,
  WalletCards,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

const sections = [
  { id: "explore", label: "Bắt đầu khám phá" },
  { id: "account", label: "Tạo tài khoản" },
  { id: "dossier", label: "Gửi hồ sơ" },
  { id: "tracking", label: "Theo dõi xử lý" },
  { id: "payment", label: "Thanh toán hồ sơ" },
  { id: "wallet", label: "Kết nối ví" },
  { id: "verification", label: "Xác minh chứng thư" },
  { id: "security", label: "Bảo vệ thông tin" },
  { id: "support", label: "Cần hỗ trợ" },
] as const;

const dossierSteps = [
  {
    title: "Chọn tư cách gửi",
    detail:
      "Chọn Cá nhân nếu hồ sơ do bạn đứng tên; chọn Doanh nghiệp hoặc tổ chức nếu bạn được đơn vị ủy quyền gửi.",
  },
  {
    title: "Chọn loại hồ sơ",
    detail:
      "Chọn đúng danh mục tài sản hoặc tác phẩm. Hệ thống sẽ dùng lựa chọn này để hiển thị biểu mẫu và yêu cầu tài liệu phù hợp.",
  },
  {
    title: "Khai thông tin",
    detail:
      "Điền tên tác phẩm hoặc tài sản, chủ thể liên quan, nguồn gốc và mô tả ngắn gọn. Chỉ chọn phạm vi hiển thị phù hợp với mục đích gửi.",
  },
  {
    title: "Tải tài liệu",
    detail:
      "Tải lên các tệp được yêu cầu, giữ nội dung rõ ràng và đặt tên dễ nhận biết. Kiểm tra lại tệp đã chọn trước khi chuyển bước.",
  },
  {
    title: "Kiểm tra và gửi",
    detail:
      "Rà soát thông tin, tài liệu và phạm vi công khai lần cuối. Sau khi gửi, hồ sơ chuyển sang chế độ theo dõi; bạn chỉ chỉnh sửa khi hệ thống yêu cầu bổ sung.",
  },
] as const;

function GuideSection({
  id,
  number,
  icon: Icon,
  title,
  children,
}: {
  id: string;
  number: string;
  icon: typeof BookOpen;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="user-guide-section" id={id}>
      <div className="user-guide-section__heading">
        <span>{number}</span>
        <Icon aria-hidden="true" size={24} strokeWidth={1.7} />
        <h2>{title}</h2>
      </div>
      <div className="user-guide-section__body">{children}</div>
    </section>
  );
}

export default function UserGuidePage() {
  return (
    <div className="user-guide-page">
      <header className="user-guide-hero">
        <div>
          <p>HƯỚNG DẪN SỬ DỤNG</p>
          <h1>Hướng dẫn sử dụng Đề cử Tinh Hoa Việt</h1>
          <p>
            Bạn muốn xem một tác phẩm, gửi hồ sơ hay xử lý công việc được phân
            công? Chọn lối đi phù hợp bên dưới. Mỗi phần giải thích bạn cần
            chuẩn bị gì, thực hiện ở đâu và điều gì sẽ xảy ra tiếp theo.
          </p>
        </div>
      </header>

      <section
        aria-label="Chọn hướng dẫn phù hợp"
        className="user-guide-journeys"
      >
        <article>
          <Search aria-hidden="true" />
          <div>
            <p>DÀNH CHO NGƯỜI XEM</p>
            <h2>Khám phá các tác phẩm đã công bố</h2>
            <p>
              Duyệt thư viện, đọc câu chuyện phía sau từng tác phẩm và đối chiếu
              thông tin xác thực đã được công bố. Các nội dung công khai có thể
              xem mà không cần đăng nhập.
            </p>
            <Link href="/works">Mở thư viện đề cử</Link>
          </div>
        </article>
        <article>
          <FileText aria-hidden="true" />
          <div>
            <p>DÀNH CHO NGƯỜI GỬI HỒ SƠ</p>
            <h2>Tạo hồ sơ và theo dõi tiến trình</h2>
            <p>
              Tạo bản nháp, chuẩn bị tài liệu theo đúng loại hồ sơ, gửi để kiểm
              tra và theo dõi yêu cầu bổ sung trong Không gian của tôi.
            </p>
            <Link href="/dashboard">Đến không gian của tôi</Link>
          </div>
        </article>
      </section>

      <div className="user-guide-layout">
        <aside className="user-guide-toc">
          <p>TRONG HƯỚNG DẪN NÀY</p>
          <nav aria-label="Mục lục hướng dẫn">
            {sections.map((section, index) => (
              <a href={`#${section.id}`} key={section.id}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                {section.label}
              </a>
            ))}
          </nav>
        </aside>

        <article className="user-guide-content">
          <GuideSection
            icon={BookOpen}
            id="explore"
            number="01"
            title="Khám phá tác phẩm"
          >
            <p>
              Bạn có thể bắt đầu từ thư viện công khai và đi thẳng tới trang chi
              tiết của từng tác phẩm. Mỗi trang tập hợp câu chuyện, chủ thể, tổ
              chức liên quan và trạng thái xác thực trong cùng một nơi.
            </p>
            <ol className="user-guide-checklist">
              <li>
                Mở <Link href="/works">Đề cử</Link> để xem tác phẩm dưới dạng
                thư viện trực quan.
              </li>
              <li>
                Dùng ô tìm kiếm và bộ lọc danh mục, chủ đề hoặc thời gian để thu
                hẹp kết quả.
              </li>
              <li>
                Chọn một tác phẩm để đọc câu chuyện, tác giả, tổ chức và thông
                tin xác thực đã được phép công bố.
              </li>
              <li>
                Nếu có mã QR hoặc đường dẫn xác minh, mở để đối chiếu chứng thư
                và dấu vết giao dịch tương ứng với tác phẩm.
              </li>
            </ol>
            <div className="user-guide-note">
              <ShieldCheck aria-hidden="true" />
              <p>
                Chỉ thông tin được phê duyệt mới xuất hiện công khai. Tài liệu
                riêng tư của hồ sơ không hiển thị trong thư viện.
              </p>
            </div>
          </GuideSection>

          <GuideSection
            icon={UserRound}
            id="account"
            number="02"
            title="Tạo tài khoản và đăng nhập"
          >
            <div className="user-guide-columns">
              <div>
                <h3>Tạo tài khoản</h3>
                <p>
                  Chọn <Link href="/register">Đăng ký</Link>, nhập email và mật
                  khẩu theo yêu cầu. Mở liên kết xác minh trong email rồi quay
                  lại đăng nhập để bắt đầu sử dụng Không gian của tôi.
                </p>
              </div>
              <div>
                <h3>Đăng nhập an toàn</h3>
                <p>
                  Truy cập <Link href="/login">Đăng nhập</Link> bằng email và
                  mật khẩu, hoặc chọn Google nếu tài khoản đã liên kết. Khi hệ
                  thống yêu cầu mã xác thực, nhập mã trên ứng dụng bảo mật của
                  bạn.
                </p>
              </div>
            </div>
            <p>
              Sau khi đăng nhập, chọn <strong>Không gian của tôi</strong> để mở
              bảng tổng quan. Hồ sơ, chứng thư, thông báo và lịch sử hoạt động
              được tập hợp tại đây; bạn có thể tiếp tục bản nháp bất cứ lúc nào.
            </p>
          </GuideSection>

          <GuideSection
            icon={FileCheck2}
            id="dossier"
            number="03"
            title="Tạo và gửi hồ sơ"
          >
            <p>
              Hồ sơ được tiếp nhận theo từng giai đoạn. Nếu cổng gửi chưa mở,
              bạn vẫn có thể hoàn thiện thông tin và lưu bản nháp để sẵn sàng
              khi chương trình tiếp nhận.
            </p>
            <ol className="user-guide-steps">
              {dossierSteps.map((step, index) => (
                <li key={step.title}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>{step.title}</h3>
                    <p>{step.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
            <div className="user-guide-note user-guide-note--warning">
              <CircleHelp aria-hidden="true" />
              <p>
                Không tải lên mật khẩu, mã xác thực, cụm từ khôi phục, khóa ví
                hoặc dữ liệu không liên quan. Chỉ cung cấp tài liệu cần thiết để
                chứng minh nội dung hồ sơ.
              </p>
            </div>
          </GuideSection>

          <GuideSection
            icon={Bell}
            id="tracking"
            number="04"
            title="Theo dõi hồ sơ và thông báo"
          >
            <p>
              Mở <Link href="/dossiers">Hồ sơ của tôi</Link> để xem trạng thái
              và phiên bản hiện tại. Biểu tượng chuông ở góc trên hiển thị số
              thông báo chưa đọc; chọn một thông báo để mở đúng hồ sơ hoặc công
              việc liên quan.
            </p>
            <div className="user-guide-note">
              <Bell aria-hidden="true" />
              <p>
                Thông báo nghiệp vụ chỉ hiển thị trong tài khoản trên website.
                Hệ thống hiện chưa gửi thông báo về hồ sơ, công việc hoặc kết
                quả xử lý qua email. Email xác minh và đặt lại mật khẩu là thư
                bảo mật do Firebase gửi, không phải thông báo nghiệp vụ.
              </p>
            </div>
            <dl className="user-guide-statuses">
              <div>
                <dt>Bản nháp</dt>
                <dd>Bạn vẫn có thể cập nhật thông tin và tài liệu.</dd>
              </div>
              <div>
                <dt>Đã gửi / Đang xử lý</dt>
                <dd>
                  Hồ sơ đang được kiểm tra, thẩm định hoặc xem xét theo quy
                  trình; nội dung tạm thời ở chế độ chỉ đọc.
                </dd>
              </div>
              <div>
                <dt>Cần bổ sung</dt>
                <dd>
                  Mở thông báo, đọc rõ từng yêu cầu, cập nhật đúng phần được nêu
                  rồi gửi lại hồ sơ.
                </dd>
              </div>
              <div>
                <dt>Được phê duyệt</dt>
                <dd>
                  Theo dõi các bước tiếp theo như hoàn tất lệ phí, xác lập
                  blockchain, phát hành chứng thư và công bố nếu đủ điều kiện.
                </dd>
              </div>
            </dl>
          </GuideSection>

          <GuideSection
            icon={CreditCard}
            id="payment"
            number="05"
            title="Thanh toán hồ sơ"
          >
            <p>
              Khi hồ sơ đủ điều kiện thanh toán, hệ thống sẽ gửi thông báo trong
              tài khoản của bạn. Mở hồ sơ, kiểm tra số tiền chính xác và nội
              dung khoản phí trước khi thanh toán, sau đó chọn nút thanh toán để
              mở trang PayOS.
            </p>
            <ol className="user-guide-checklist">
              <li>
                Đối chiếu mã hồ sơ, nội dung khoản phí và số tiền cần trả.
              </li>
              <li>
                Quét mã QR bằng ứng dụng ngân hàng hoặc làm theo hướng dẫn trên
                trang thanh toán.
              </li>
              <li>
                Không sửa nội dung chuyển khoản. Sau khi trả tiền, chờ hệ thống
                cập nhật kết quả rồi quay lại hồ sơ.
              </li>
              <li>
                Nếu đã bị trừ tiền nhưng trạng thái chưa đổi, không thanh toán
                lần hai; hãy giữ biên lai và liên hệ hỗ trợ.
              </li>
            </ol>
            <div className="user-guide-note">
              <ShieldCheck aria-hidden="true" />
              <p>
                TMI không yêu cầu số thẻ, mã bảo mật thẻ hoặc mật khẩu ngân hàng
                trong hồ sơ. Việc thanh toán chỉ thực hiện trên trang PayOS được
                mở từ chính hồ sơ của bạn.
              </p>
            </div>
          </GuideSection>

          <GuideSection
            icon={WalletCards}
            id="wallet"
            number="06"
            title="Kết nối ví và ghi nhận hồ sơ"
          >
            <p>
              Phần này dành cho nhân sự được giao nhiệm vụ ghi nhận hồ sơ đã phê
              duyệt. Bạn có thể dùng MetaMask, Rabby, Coinbase hoặc
              WalletConnect. Hệ thống chỉ yêu cầu xác nhận bằng ví của tổ chức,
              không yêu cầu nhập khóa bí mật.
            </p>
            <ol className="user-guide-steps">
              <li>
                <span>01</span>
                <div>
                  <h3>Chọn ví</h3>
                  <p>
                    Mở mục Ký blockchain, chọn Kết nối ví rồi chọn ứng dụng ví
                    đang sử dụng. Với điện thoại, WalletConnect sẽ hiển thị mã
                    QR hoặc mở ứng dụng ví phù hợp.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>Xác nhận đúng tài khoản</h3>
                  <p>
                    Kiểm tra địa chỉ ví hiển thị trên màn hình. Nếu hệ thống báo
                    sai ví hoặc sai mạng, đổi sang đúng tài khoản và Polygon
                    Mainnet rồi thử lại.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Kiểm tra hồ sơ trước khi ký</h3>
                  <p>
                    Đối chiếu tên hồ sơ, phiên bản và dấu vân tay số. Chỉ tiếp
                    tục khi thông tin khớp với hồ sơ đã được phê duyệt.
                  </p>
                </div>
              </li>
              <li>
                <span>04</span>
                <div>
                  <h3>Chờ mạng xác nhận</h3>
                  <p>
                    Sau khi đồng ý trong ví, giữ trang mở cho đến khi hệ thống
                    báo Đã ghi nhận. Nếu giao dịch đang chờ, không ký lại cùng
                    một hồ sơ.
                  </p>
                </div>
              </li>
            </ol>
            <div className="user-guide-note user-guide-note--warning">
              <CircleHelp aria-hidden="true" />
              <p>
                Không cung cấp cụm từ khôi phục hoặc khóa bí mật cho bất kỳ ai.
                Nếu ví báo thiếu phí, sai mạng hoặc giao dịch thất bại, dừng
                thao tác và báo bộ phận vận hành.
              </p>
            </div>
          </GuideSection>

          <GuideSection
            icon={QrCode}
            id="verification"
            number="07"
            title="Tra cứu chứng thư và mã QR"
          >
            <ol className="user-guide-checklist">
              <li>
                Mở <Link href="/verify">Tra cứu chứng thư</Link> hoặc quét mã QR
                trên chứng thư.
              </li>
              <li>Nhập số chứng thư hoặc mã giao dịch được cung cấp.</li>
              <li>
                Đối chiếu tên tài sản, phiên bản, thời điểm, trạng thái và dấu
                vết giao dịch trên trang kết quả với thông tin bạn được cung
                cấp.
              </li>
            </ol>
            <div className="user-guide-proof">
              <CheckCircle2 aria-hidden="true" />
              <div>
                <h3>Blockchain ghi nhận điều gì?</h3>
                <p>
                  Hệ thống không lưu tệp gốc hoặc dữ liệu cá nhân lên
                  blockchain. Blockchain chỉ ghi nhận mã băm bằng chứng, phiên
                  bản và thông tin giao dịch để hỗ trợ đối chiếu tính toàn vẹn.
                </p>
              </div>
            </div>
            <Link className="user-guide-action" href="/verify">
              Tra cứu chứng thư
            </Link>
          </GuideSection>

          <GuideSection
            icon={ShieldCheck}
            id="security"
            number="08"
            title="Bảo vệ tài khoản và dữ liệu"
          >
            <ol className="user-guide-checklist">
              <li>
                Dùng mật khẩu riêng cho tài khoản THV và hoàn tất xác thực nhiều
                lớp khi hệ thống yêu cầu.
              </li>
              <li>
                Chỉ tải lên tài liệu liên quan trực tiếp đến hồ sơ; giữ bản gốc
                để đối chiếu khi cần.
              </li>
              <li>
                Kiểm tra đúng tên miền trước khi đăng nhập, quét mã QR hoặc mở
                liên kết xác minh.
              </li>
              <li>
                Đăng xuất sau khi làm việc trên thiết bị dùng chung và báo ngay
                khi phát hiện hoạt động bất thường.
              </li>
            </ol>
            <div className="user-guide-note user-guide-note--warning">
              <CircleHelp aria-hidden="true" />
              <p>
                THV không bao giờ yêu cầu bạn cung cấp mật khẩu, mã xác thực,
                cụm từ khôi phục hoặc khóa ví. Không gửi những thông tin này qua
                email, tin nhắn hay biểu mẫu hỗ trợ.
              </p>
            </div>
          </GuideSection>

          <GuideSection
            icon={CircleHelp}
            id="support"
            number="09"
            title="Khi bạn cần hỗ trợ"
          >
            <div className="user-guide-faq">
              <details>
                <summary>Không thể đăng nhập vào tài khoản</summary>
                <p>
                  Kiểm tra lại email, mật khẩu và kết nối mạng. Nếu tài khoản đã
                  được tạo nhưng vẫn không thể truy cập, chụp lại thông báo lỗi
                  và liên hệ quản trị hệ thống để kiểm tra trạng thái hoặc liên
                  kết tài khoản.
                </p>
              </details>
              <details>
                <summary>
                  Quên mật khẩu hoặc chưa nhận được email đặt lại
                </summary>
                <p>
                  Chọn Quên mật khẩu tại trang đăng nhập, nhập đúng email đã
                  đăng ký rồi kiểm tra hộp thư đến và thư rác. Liên kết bảo mật
                  chỉ dùng được một lần; nếu hết hạn, quay lại trang Quên mật
                  khẩu để gửi yêu cầu mới. Vì lý do bảo mật, hệ thống không xác
                  nhận email có tồn tại hay không.
                </p>
              </details>
              <details>
                <summary>Không thể tiếp tục tạo hồ sơ</summary>
                <p>
                  Kiểm tra các trường bắt buộc, loại hồ sơ và yêu cầu tài liệu.
                  Nếu phiên đăng nhập hết hạn, đăng nhập lại rồi mở bản nháp từ
                  Hồ sơ của tôi để tiếp tục.
                </p>
              </details>
              <details>
                <summary>Tài liệu tải lên không thành công</summary>
                <p>
                  Đọc định dạng và giới hạn tệp ngay tại vùng tải lên; đổi tên
                  tệp ngắn, rõ ràng, kiểm tra kết nối rồi thử lại. Nếu lỗi lặp
                  lại, ghi lại tên tệp và thông báo hiển thị để được hỗ trợ.
                </p>
              </details>
              <details>
                <summary>Tra cứu nhưng chưa thấy chứng thư</summary>
                <p>
                  Kiểm tra lại từng ký tự của mã và chờ quy trình phát hành hoàn
                  tất. Chứng thư chỉ tra cứu được sau khi dữ liệu xác lập đã
                  được ghi nhận thành công.
                </p>
              </details>
            </div>
            <p className="user-guide-support-copy">
              Để được hỗ trợ nhanh hơn, hãy cung cấp email tài khoản, mã hồ sơ,
              thời điểm xảy ra sự cố, thiết bị đang dùng và ảnh chụp thông báo
              lỗi. Mô tả thao tác cuối cùng bạn đã thực hiện; không gửi mật
              khẩu, mã xác thực hoặc khóa ví.
            </p>
          </GuideSection>
        </article>
      </div>
    </div>
  );
}
