import { ArrowRight, Bell, BookOpen, Building2, Download, FileCheck2, LockKeyhole, Send, ShieldCheck, UserRound } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

const nav = [["about", "Về tổ chức"], ["explore", "Đề cử"], ["account", "Tài khoản"], ["dossier", "Hồ sơ"], ["tracking", "Theo dõi"], ["certificate", "Chứng thư"], ["install", "Cài ứng dụng"], ["security", "An toàn"]] as const;

export default function UserGuidePage() {
  return (
    <div className="project-guide public-theme-surface min-h-screen px-4 py-10 sm:px-6 sm:py-16 lg:px-8">
      <main className="mx-auto max-w-6xl">
        <header className="max-w-4xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">Trợ giúp sử dụng</p>
          <h1 className="mt-4 text-4xl font-bold tracking-[-0.04em] text-white sm:text-6xl">Hướng dẫn sử dụng Đề cử Tinh Hoa Việt</h1>
          <p className="mt-5 max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">Chọn đúng việc bạn cần làm. Hướng dẫn này chỉ mô tả các chức năng đang có trên hệ thống.</p>
        </header>
        <nav aria-label="Nội dung hướng dẫn" className="mt-9 flex gap-2 overflow-x-auto border-y border-white/10 py-4">
          {nav.map(([id, label]) => <a className="shrink-0 rounded-full border border-white/15 px-4 py-2 text-sm font-bold text-slate-200 hover:border-gold-300 hover:text-gold-300" href={`#${id}`} key={id}>{label}</a>)}
        </nav>

        <div className="mt-12 grid gap-10 lg:grid-cols-2">
          <Section icon={Building2} id="about" number="01" title="Về Tổ chức Đề cử và Xác lập Tinh Hoa Việt" wide>
            <p className="max-w-4xl text-base leading-8">Tổ chức Đề cử và Xác lập Tinh Hoa Việt được hình thành với mong muốn tìm kiếm, ghi nhận và lan tỏa những giá trị tiêu biểu do người Việt kiến tạo. Đó có thể là một tác phẩm, sản phẩm, sáng kiến, di sản hoặc câu chuyện mang giá trị văn hóa và đóng góp tích cực cho cộng đồng.</p>
            <p className="max-w-4xl text-base leading-8">Tổ chức đồng hành trong toàn bộ hành trình: tiếp nhận thông tin đề cử, điều phối quá trình xem xét, yêu cầu bổ sung khi cần, công bố nội dung đủ điều kiện và phát hành chứng thư xác lập. Mỗi bước đều hướng tới một mục tiêu chung—giúp thông tin được trình bày rõ ràng, có nguồn đối chiếu và có thể kiểm tra lại theo thời gian.</p>
            <div className="about-columns grid gap-8 border-y border-[var(--theme-border)] py-6 md:grid-cols-2 md:divide-x md:divide-[var(--theme-border)]">
              <AboutCard title="Chứng thư mang lại điều gì?">Chứng thư là dấu mốc ghi nhận một hồ sơ cụ thể tại một thời điểm cụ thể. Trên đó có số chứng thư, phiên bản và dấu vân tay số để người xem kiểm tra thông tin đã công bố có còn nguyên vẹn hay không. Chứng thư hỗ trợ minh bạch nguồn gốc ghi nhận; không tự thay thế giấy chứng nhận sở hữu, quyền tác giả hoặc kết luận của cơ quan chuyên ngành.</AboutCard>
              <AboutCard title="Thông tin nào được công khai?">Thư viện chỉ giới thiệu những nội dung đã được lựa chọn và cho phép công bố, chẳng hạn tên đề cử, câu chuyện, hình ảnh đại diện và trạng thái chứng thư. Tài liệu nội bộ, thông tin liên hệ, giấy tờ cá nhân và các tệp dùng trong quá trình xem xét vẫn được bảo vệ theo quyền truy cập, không xuất hiện trên trang công khai.</AboutCard>
            </div>
          </Section>

          <Section icon={BookOpen} id="explore" number="02" title="Khám phá đề cử">
            <p>Mở danh sách đề cử để xem nội dung đã được duyệt và công bố. Bạn không cần đăng nhập để tìm kiếm, mở chi tiết hoặc chia sẻ.</p>
            <Steps items={["Tìm theo tên hoặc dùng bộ lọc.", "Mở đề cử để xem câu chuyện, hình ảnh và thông tin chủ thể.", "Nếu đã có chứng thư, chọn Xem và kiểm tra chứng thư."]} />
            <GuideLink href="/works">Mở thư viện đề cử</GuideLink>
          </Section>

          <Section icon={UserRound} id="account" number="03" title="Tạo tài khoản và đăng nhập">
            <p>Tạo tài khoản khi bạn cần gửi và theo dõi hồ sơ. Sau khi đăng ký, xác minh email rồi đăng nhập để mở không gian cá nhân.</p>
            <Steps items={["Chọn Đăng ký và nhập email đang sử dụng.", "Mở email xác minh do hệ thống gửi.", "Đăng nhập; dùng Đặt lại mật khẩu nếu quên mật khẩu."]} />
            <div className="grid gap-3 sm:flex"><GuideLink href="/register">Đăng ký</GuideLink><GuideLink href="/login" secondary>Đăng nhập</GuideLink></div>
          </Section>

          <Section icon={Send} id="dossier" number="04" title="Tạo và gửi hồ sơ đề cử">
            <p>Trong Hồ sơ của tôi, tạo bản nháp, chọn loại hồ sơ và khai thông tin theo biểu mẫu.</p>
            <Steps items={["Lưu bản nháp trong khi chuẩn bị.", "Kiểm tra tên, chủ thể, mô tả và từng tệp trước khi gửi.", "Sau khi gửi, hồ sơ chuyển sang chỉ đọc trong thời gian xử lý."]} />
            <Note>Không tải lên mật khẩu, mã xác thực, khóa ví hoặc dữ liệu không liên quan. Nếu cổng tiếp nhận chưa mở, hệ thống sẽ thông báo tại khu vực hồ sơ.</Note>
          </Section>

          <Section icon={Bell} id="tracking" number="05" title="Theo dõi hồ sơ, bổ sung và lệ phí">
            <p>Trạng thái và thông báo nghiệp vụ xuất hiện trong tài khoản trên website. Mở thông báo để đi đúng tới hồ sơ hoặc bước liên quan.</p>
            <Steps items={["Cần bổ sung: cập nhật đúng phần được yêu cầu rồi gửi lại.", "Được phê duyệt: theo dõi nghĩa vụ lệ phí nếu có.", "Thanh toán: kiểm tra mã hồ sơ, nội dung và số tiền trước khi mở cổng thanh toán; không thanh toán lần hai nếu trạng thái cập nhật chậm."]} />
          </Section>

          <Section icon={FileCheck2} id="certificate" number="06" title="Tra cứu chứng thư, QR và lưu trữ blockchain">
            <p>Trang tra cứu là công khai. Nhập số chứng thư hoặc mã giao dịch để xem trạng thái, phiên bản và bằng chứng ghi nhận.</p>
            <Steps items={["Mở từ nút trên đề cử hoặc vào trang Tra cứu chứng thư.", "QR trên chứng thư mở trực tiếp đúng trang xác minh.", "Tài liệu đối chiếu là tệp bạn đang giữ; trình duyệt tính dấu vân tay để so khớp dữ liệu đã công bố."]} />
            <div className="grid gap-5"><Note>Blockchain lưu dấu vân tay số của dữ liệu xác lập, số phiên bản, địa chỉ hợp đồng và dấu vết giao dịch. Các bản ghi này hỗ trợ phát hiện dữ liệu đã bị thay đổi.</Note><Note>Blockchain không lưu ảnh, video, tệp gốc, mật khẩu hay tài liệu cá nhân. Tệp được quản lý trong hệ thống lưu trữ riêng theo quyền truy cập; chỉ dấu vân tay một chiều được dùng để đối chiếu.</Note></div>
            <GuideLink href="/verify">Tra cứu chứng thư</GuideLink>
          </Section>

          <Section icon={Download} id="install" number="07" title="Cài ứng dụng trên thiết bị">
            <p>Nút Cài ứng dụng trên thanh đầu trang đưa bạn tới hướng dẫn. Việc cài chỉ bắt đầu sau khi bạn chọn Tiến hành cài đặt.</p>
            <Steps items={["iPhone/iPad: mở Chia sẻ → Thêm vào Màn hình chính.", "Android: mở menu trình duyệt → Cài đặt ứng dụng hoặc Thêm vào màn hình chính.", "Máy tính: mở menu trình duyệt → Cài đặt ứng dụng."]} />
            <GuideLink href="/install">Xem hướng dẫn cài đặt</GuideLink>
          </Section>

          <Section icon={LockKeyhole} id="security" number="08" title="Bảo vệ tài khoản và nhận hỗ trợ" wide>
            <div className="grid gap-7 md:grid-cols-2"><div><h3 className="font-bold text-white">Giữ tài khoản an toàn</h3><Steps items={["Dùng mật khẩu riêng và không chia sẻ mã xác thực.", "Không cung cấp cụm từ khôi phục hoặc khóa ví cho bất kỳ ai.", "Đăng xuất sau khi dùng thiết bị chung."]} /></div><div><h3 className="font-bold text-white">Khi gặp sự cố</h3><Steps items={["Ghi lại mã hồ sơ hoặc số chứng thư.", "Chụp lỗi và ghi thời điểm, thiết bị, trình duyệt.", "Không gửi mật khẩu, mã xác thực hoặc khóa ví cho bộ phận hỗ trợ."]} /></div></div>
          </Section>
        </div>
      </main>
    </div>
  );
}

function Section({ children, icon: Icon, id, number, title, wide = false }: { children: ReactNode; icon: typeof BookOpen; id: string; number: string; title: string; wide?: boolean }) {
  return <section className={`scroll-mt-28 border-t border-white/15 pt-6 ${wide ? "lg:col-span-2" : ""}`} id={id}><div className="flex items-center justify-between"><Icon className="size-6 text-gold-300" /><span className="font-mono text-xs text-slate-500">{number}</span></div><h2 className="mt-4 text-2xl font-bold text-white">{title}</h2><div className="mt-4 space-y-5 text-sm leading-7 text-slate-300">{children}</div></section>;
}
function Steps({ items }: { items: string[] }) { return <ol className="space-y-3">{items.map((item, index) => <li className="flex gap-3" key={item}><span className="grid size-7 shrink-0 place-items-center rounded-full border border-white/15 font-mono text-xs text-gold-300">{index + 1}</span><span>{item}</span></li>)}</ol>; }
function Note({ children }: { children: ReactNode }) { return <div className="flex gap-3 border-l-2 border-gold-300 bg-[var(--theme-surface-soft)] p-4"><ShieldCheck className="mt-1 size-4 shrink-0 text-gold-300" /><p>{children}</p></div>; }
function AboutCard({ children, title }: { children: ReactNode; title: string }) { return <article className="md:px-7 md:first:pl-0 md:last:pr-0"><ShieldCheck className="size-5 text-primary-700" /><h3 className="mt-4 text-lg font-bold text-white">{title}</h3><p className="mt-3 leading-7">{children}</p></article>; }
function GuideLink({ children, href, secondary = false }: { children: ReactNode; href: string; secondary?: boolean }) { return <Link className={`guide-cta group inline-flex min-h-12 w-full items-center justify-between gap-4 rounded-xl border px-5 py-3 text-sm font-extrabold no-underline sm:w-auto ${secondary ? "border-[var(--theme-border)] bg-[var(--theme-surface)] text-[var(--theme-text)] hover:border-primary-700 hover:text-primary-700" : "border-primary-800 bg-primary-800 text-white shadow-sm hover:bg-primary-900"}`} href={href}><span>{children}</span><ArrowRight aria-hidden="true" className="guide-cta__icon size-4 shrink-0" /></Link>; }
