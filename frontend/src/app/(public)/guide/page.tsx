import {
  ArrowRight,
  Bell,
  BookOpen,
  Download,
  FileCheck2,
  ListChecks,
  LockKeyhole,
  Send,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

const nav = [
  ["about", "Bắt đầu"],
  ["explore", "Đề cử"],
  ["account", "Tài khoản"],
  ["dossier", "Hồ sơ"],
  ["tracking", "Theo dõi"],
  ["certificate", "Chứng thư"],
  ["install", "Cài ứng dụng"],
  ["security", "An toàn"],
] as const;

export default function UserGuidePage() {
  return (
    <div className="project-guide public-theme-surface min-h-screen px-4 py-10 sm:px-6 sm:py-16 lg:px-8">
      <main className="mx-auto max-w-6xl">
        <header className="max-w-4xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">
            Trợ giúp sử dụng
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] text-white sm:text-6xl">
            Hướng dẫn sử dụng Đề cử Tinh Hoa Việt
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">
            Tìm đúng việc cần làm: xem đề cử đã công bố, gửi hồ sơ, theo dõi
            tiến độ hoặc kiểm tra chứng thư. Các bước dưới đây đi theo trình tự
            sử dụng trên hệ thống.
          </p>
        </header>
        <nav
          aria-label="Nội dung hướng dẫn"
          className="mt-9 flex gap-2 overflow-x-auto border-y border-white/10 py-4"
        >
          {nav.map(([id, label]) => (
            <a
              className="shrink-0 rounded-full border border-white/15 px-4 py-2 text-sm font-bold text-slate-200 hover:border-gold-300 hover:text-gold-300"
              href={`#${id}`}
              key={id}
            >
              {label}
            </a>
          ))}
        </nav>

        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          <Section
            icon={ListChecks}
            id="about"
            number="01"
            title="Chọn việc bạn cần làm"
            wide
          >
            <p>
              Tinh Hoa Việt là tổ chức tiếp nhận và xem xét hồ sơ đề cử. Chọn lộ
              trình phù hợp với việc bạn muốn hoàn thành:
            </p>
            <Steps
              items={[
                "Muốn xem nội dung đã công bố: mở thư viện đề cử. Bạn không cần tài khoản.",
                "Muốn gửi đề cử: tạo tài khoản, chuẩn bị thông tin và tài liệu, rồi gửi hồ sơ.",
                "Đã gửi hồ sơ: đăng nhập để xem trạng thái, bổ sung thông tin hoặc thanh toán khi được yêu cầu.",
                "Đã có chứng thư: dùng số chứng thư, mã giao dịch hoặc mã QR để tra cứu.",
              ]}
            />
            <div className="flex flex-wrap gap-3">
              <GuideLink href="/works">Xem đề cử</GuideLink>
              <GuideLink href="/dossiers" secondary>
                Theo dõi hồ sơ
              </GuideLink>
            </div>
          </Section>

          <Section
            icon={BookOpen}
            id="explore"
            number="02"
            title="Khám phá đề cử"
          >
            <p>Bạn không cần đăng nhập để tìm và xem những đề cử đã công bố.</p>
            <Steps
              items={[
                "Mở thư viện đề cử; nhập tên cần tìm hoặc chọn bộ lọc.",
                "Chọn một đề cử để đọc nội dung và xem hình ảnh đã công bố.",
                "Nếu có chứng thư, mở mục chứng thư từ trang chi tiết để kiểm tra.",
              ]}
            />
            <p>
              Kết quả: trang chi tiết hiển thị nội dung được phép công bố. Tài
              liệu thẩm định, thông tin liên hệ và giấy tờ cá nhân không xuất
              hiện trong thư viện.
            </p>
            <GuideLink href="/works">Mở thư viện đề cử</GuideLink>
          </Section>

          <Section
            icon={UserRound}
            id="account"
            number="03"
            title="Tạo tài khoản và đăng nhập"
          >
            <p>
              Cần có tài khoản để tạo và theo dõi hồ sơ. Hãy dùng địa chỉ email
              bạn có thể truy cập trong suốt quá trình xử lý.
            </p>
            <Steps
              items={[
                "Chọn Đăng ký, điền thông tin và gửi biểu mẫu.",
                "Mở email xác minh và làm theo liên kết trong thư.",
                "Quay lại trang Đăng nhập. Nếu quên mật khẩu, chọn Quên mật khẩu? để nhận liên kết đặt lại.",
              ]}
            />
            <p>
              Kết quả: đăng nhập thành công và mở được khu vực Hồ sơ của tôi.
              Nếu chưa thấy email xác minh, kiểm tra cả mục Thư rác trước khi
              yêu cầu gửi lại.
            </p>
            <div className="grid gap-3 sm:flex">
              <GuideLink href="/register">Đăng ký</GuideLink>
              <GuideLink href="/login" secondary>
                Đăng nhập
              </GuideLink>
            </div>
          </Section>

          <Section
            icon={Send}
            id="dossier"
            number="04"
            title="Tạo và gửi hồ sơ đề cử"
          >
            <p>
              Đăng nhập và mở Hồ sơ của tôi. Bạn có thể lưu bản nháp để hoàn
              thiện trước khi gửi.
            </p>
            <Steps
              items={[
                "Chọn Tạo hồ sơ, chọn loại phù hợp và điền các trường trong biểu mẫu.",
                "Tải tài liệu liên quan lên, kiểm tra tên, chủ thể, mô tả và từng tệp.",
                "Gửi hồ sơ khi thông tin đã đầy đủ; kiểm tra trạng thái trong danh sách Hồ sơ của tôi.",
              ]}
            />
            <Note>
              Sau khi gửi, hồ sơ tạm thời chỉ đọc. Khi cần chỉnh sửa, hãy chờ
              yêu cầu bổ sung. Không tải lên mật khẩu, mã xác thực hoặc dữ liệu
              không liên quan.
            </Note>
            <p>
              Kết quả: hồ sơ xuất hiện trong danh sách với trạng thái đã tiếp
              nhận. Nếu vẫn là bản nháp, mở lại hồ sơ và hoàn tất bước gửi.
            </p>
            <GuideLink href="/dossiers">Mở Hồ sơ của tôi</GuideLink>
          </Section>

          <Section
            icon={Bell}
            id="tracking"
            number="05"
            title="Theo dõi hồ sơ, bổ sung và lệ phí"
          >
            <p>
              Mở Hồ sơ của tôi để xem trạng thái mới nhất. Thông báo trong tài
              khoản sẽ dẫn đến hồ sơ hoặc việc bạn cần xử lý.
            </p>
            <Steps
              items={[
                "Khi hồ sơ cần bổ sung, đọc yêu cầu, cập nhật đúng phần được nêu và gửi lại.",
                "Khi hồ sơ được duyệt, kiểm tra khoản lệ phí được hiển thị trong tài khoản, nếu có.",
                "Trước khi thanh toán, đối chiếu mã hồ sơ, nội dung và số tiền. Nếu đã trả tiền mà trạng thái chưa đổi, không thanh toán lần hai; kiểm tra lại sau hoặc liên hệ hỗ trợ.",
              ]}
            />
            <p>
              Sau mỗi thao tác, quay lại hồ sơ để kiểm tra trạng thái mới. Giữ
              mã hồ sơ và thông tin giao dịch để đối chiếu khi cần hỗ trợ.
            </p>
            <GuideLink href="/dossiers">Xem trạng thái hồ sơ</GuideLink>
          </Section>

          <Section
            icon={FileCheck2}
            id="certificate"
            number="06"
            title="Tra cứu và kiểm tra chứng thư"
          >
            <p>
              Trang tra cứu mở cho mọi người, không cần đăng nhập. Bạn có thể
              nhập số chứng thư, mã giao dịch hoặc quét mã QR trên chứng thư.
            </p>
            <Steps
              items={[
                "Mở trang Tra cứu chứng thư, chọn cách tra cứu và nhập số chứng thư hoặc mã giao dịch.",
                "Đọc kết quả xác minh, rồi đối chiếu số, trạng thái và phiên bản với chứng thư bạn nhận được.",
                "Nếu không tìm thấy hoặc chứng thư đang chờ xác nhận, kiểm tra lại mã và tra cứu sau; liên hệ đơn vị phát hành khi thông tin không khớp.",
              ]}
            />
            <div className="grid gap-5">
              <Note>
                Mã QR trên chứng thư dẫn đến trang xác minh tương ứng. Bản ghi
                blockchain hỗ trợ đối chiếu dấu vân tay số và lịch sử ghi nhận.
              </Note>
              <Note>
                Blockchain không lưu ảnh, video, tệp gốc hoặc tài liệu cá nhân.
                Dấu vân tay số dùng để đối chiếu dữ liệu đã ghi nhận; hãy giữ
                tài liệu gốc nếu bạn cần kiểm tra về sau.
              </Note>
            </div>
            <p>
              Chứng thư ghi nhận thông tin tại thời điểm phát hành; nó không
              thay thế giấy tờ chứng minh quyền sở hữu, quyền tác giả hoặc kết
              luận chuyên ngành.
            </p>
            <GuideLink href="/verify">Tra cứu chứng thư</GuideLink>
          </Section>

          <Section
            icon={Download}
            id="install"
            number="07"
            title="Cài ứng dụng trên thiết bị"
          >
            <p>
              Bạn có thể thêm website vào màn hình chính để mở nhanh. Cách thực
              hiện tùy thiết bị và trình duyệt.
            </p>
            <Steps
              items={[
                "Mở trang Cài ứng dụng bằng chính thiết bị muốn cài.",
                "Chọn Tiến hành cài đặt nếu trình duyệt hỗ trợ; nếu không, làm theo hướng dẫn thủ công cho thiết bị của bạn.",
                "Kiểm tra biểu tượng Tinh Hoa Việt trên màn hình chính hoặc trong danh sách ứng dụng.",
              ]}
            />
            <GuideLink href="/install">Xem hướng dẫn cài đặt</GuideLink>
          </Section>

          <Section
            icon={LockKeyhole}
            id="security"
            number="08"
            title="Bảo vệ tài khoản và nhận hỗ trợ"
            wide
          >
            <div className="grid gap-7 md:grid-cols-2">
              <div>
                <h3 className="font-bold text-white">Giữ tài khoản an toàn</h3>
                <Steps
                  items={[
                    "Dùng mật khẩu riêng và không chia sẻ mã xác thực.",
                    "Không cung cấp cụm từ khôi phục hoặc khóa ví cho bất kỳ ai.",
                    "Đăng xuất sau khi dùng thiết bị chung.",
                  ]}
                />
              </div>
              <div>
                <h3 className="font-bold text-white">Khi gặp sự cố</h3>
                <Steps
                  items={[
                    "Ghi lại mã hồ sơ hoặc số chứng thư liên quan.",
                    "Chụp thông báo lỗi và ghi thời điểm, thiết bị, trình duyệt đã dùng.",
                    "Gửi thông tin sự cố qua kênh hỗ trợ chính thức; không gửi mật khẩu, mã xác thực hoặc khóa ví.",
                  ]}
                />
              </div>
            </div>
          </Section>
        </div>
      </main>
    </div>
  );
}

function Section({
  children,
  icon: Icon,
  id,
  number,
  title,
  wide = false,
}: {
  children: ReactNode;
  icon: typeof BookOpen;
  id: string;
  number: string;
  title: string;
  wide?: boolean;
}) {
  return (
    <section
      className={`scroll-mt-28 border-t border-white/15 pt-6 ${wide ? "lg:col-span-2" : ""}`}
      id={id}
    >
      <div className="flex items-center justify-between">
        <Icon className="size-6 text-gold-300" />
        <span className="font-mono text-xs text-slate-500">{number}</span>
      </div>
      <h2 className="mt-4 text-2xl font-bold text-white">{title}</h2>
      <div className="mt-4 space-y-5 text-sm leading-7 text-slate-300">
        {children}
      </div>
    </section>
  );
}
function Steps({ items }: { items: string[] }) {
  return (
    <ol className="space-y-3">
      {items.map((item, index) => (
        <li className="flex gap-3" key={item}>
          <span className="grid size-7 shrink-0 place-items-center rounded-full border border-white/15 font-mono text-xs text-gold-300">
            {index + 1}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  );
}
function Note({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 border-l-2 border-gold-300 bg-[var(--theme-surface-soft)] p-4">
      <ShieldCheck className="mt-1 size-4 shrink-0 text-gold-300" />
      <p>{children}</p>
    </div>
  );
}
function GuideLink({
  children,
  href,
  secondary = false,
}: {
  children: ReactNode;
  href: string;
  secondary?: boolean;
}) {
  return (
    <Link
      className={`guide-cta group inline-flex min-h-12 w-full items-center justify-between gap-4 rounded-xl border px-5 py-3 text-sm font-extrabold no-underline sm:w-auto ${secondary ? "border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)] hover:border-[var(--theme-accent)] hover:text-[var(--theme-accent)]" : "guide-cta--primary shadow-sm"}`}
      href={href}
    >
      <span>{children}</span>
      <ArrowRight
        aria-hidden="true"
        className="guide-cta__icon size-4 shrink-0"
      />
    </Link>
  );
}
