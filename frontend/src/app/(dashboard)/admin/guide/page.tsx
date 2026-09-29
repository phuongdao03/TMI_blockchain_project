import {
  BadgeDollarSign,
  BookOpenCheck,
  CircleAlert,
  ClipboardCheck,
  FileClock,
  FileText,
  ShieldCheck,
  Signature,
  UsersRound,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { RoleGate } from "@/components/auth/role-gate";

const sections = [
  { href: "#start", label: "Bắt đầu ca làm việc" },
  { href: "#attendance", label: "Điểm làm việc và chấm công" },
  { href: "#employees", label: "Nhân viên và tính lương" },
  { href: "#records", label: "Hồ sơ và người dùng" },
  { href: "#review", label: "Thẩm định hồ sơ" },
  { href: "#payment", label: "Thanh toán" },
  { href: "#blockchain", label: "Ghi nhận blockchain" },
  { href: "#publication", label: "Công bố nội dung" },
  { href: "#staff", label: "Tài khoản nhân sự" },
  { href: "#audit", label: "Lịch sử và báo cáo" },
  { href: "#troubleshooting", label: "Tình huống thường gặp" },
] as const;

function GuideSection({
  id,
  icon: Icon,
  title,
  children,
}: {
  id: string;
  icon: typeof BookOpenCheck;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      className="scroll-mt-24 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
      id={id}
    >
      <div className="flex items-start gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-50 text-primary-700">
          <Icon aria-hidden="true" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-xl font-bold text-[var(--theme-text)] sm:text-2xl">
            {title}
          </h2>
          <div className="mt-4 space-y-4 text-sm leading-7 text-[var(--theme-muted)] sm:text-base">
            {children}
          </div>
        </div>
      </div>
    </section>
  );
}

function Steps({ children }: { children: ReactNode }) {
  return (
    <ol className="list-decimal space-y-2 pl-5 marker:font-bold marker:text-primary-700">
      {children}
    </ol>
  );
}

function WorkspaceLink({
  href,
  children,
}: {
  href: string;
  children: ReactNode;
}) {
  return (
    <Link
      className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] px-4 py-2 font-semibold text-[var(--theme-text)] transition-colors hover:bg-[var(--theme-elevated)] focus-visible:outline-2 focus-visible:outline-offset-2"
      href={href}
    >
      {children}
    </Link>
  );
}

export default function AdminGuidePage() {
  return (
    <RoleGate allowed={["SUPER_ADMIN"]}>
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="border-b border-[var(--theme-border)] pb-6">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary-700">
            Dành cho quản trị viên
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-4xl">
            Hướng dẫn quản trị
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--theme-muted)] sm:text-base">
            Dành cho quản trị viên Tinh Hoa Việt. Chọn công việc trong mục lục,
            làm theo thứ tự và kiểm tra kết quả trên hồ sơ trước khi chuyển sang
            bước tiếp theo.
          </p>
        </header>

        <div className="grid items-start gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 lg:sticky lg:top-24">
            <p className="px-2 text-xs font-bold uppercase tracking-[0.14em] text-[var(--theme-muted)]">
              Nội dung hướng dẫn
            </p>
            <nav
              aria-label="Mục lục hướng dẫn quản trị"
              className="mt-3 grid gap-1"
            >
              {sections.map((section) => (
                <a
                  className="rounded-lg px-3 py-2.5 text-sm font-medium text-[var(--theme-text)] transition-colors hover:bg-[var(--theme-elevated)]"
                  href={section.href}
                  key={section.href}
                >
                  {section.label}
                </a>
              ))}
            </nav>
          </aside>

          <div className="space-y-5">
            <GuideSection
              id="start"
              icon={BookOpenCheck}
              title="Bắt đầu ca làm việc"
            >
              <p>
                Mở <strong>Tổng quan vận hành</strong> đầu mỗi ca để nhận biết
                việc đang chờ và việc cần xử lý gấp.
              </p>
              <Steps>
                <li>Xem thông báo, hồ sơ quá hạn và các cảnh báo lỗi.</li>
                <li>
                  Mở từng nhóm công việc để kiểm tra trạng thái trên hồ sơ gốc.
                </li>
                <li>
                  Xử lý theo mức độ ưu tiên; chuyển cho người phụ trách nếu
                  nghiệp vụ nằm ngoài quyền của bạn.
                </li>
              </Steps>
              <WorkspaceLink href="/admin/dashboard">
                Mở tổng quan vận hành
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="attendance"
              icon={FileClock}
              title="Điểm làm việc và chấm công GPS"
            >
              <p>
                Hoàn tất điểm làm việc và chính sách vị trí trước khi phân công
                nhân viên chấm công.
              </p>
              <Steps>
                <li>
                  Tạo điểm chấm công, nhập mã và tên dễ nhận biết, rồi kích
                  hoạt.
                </li>
                <li>
                  Đặt múi giờ của điểm làm việc. Tìm địa chỉ và chọn kết quả phù
                  hợp; kiểm tra bản đồ trước khi bấm Chọn vị trí này làm tâm
                  vùng. Có thể dùng tọa độ đã xác minh hoặc GPS tại văn phòng.
                </li>
                <li>
                  Kiểm tra bán kính, sai số GPS cho phép và ngày hiệu lực; lưu
                  chính sách rồi phân công nhân viên.
                </li>
                <li>
                  Theo dõi giờ vào, giờ ra và xem bằng chứng trước khi xử lý
                  ngoại lệ vị trí.
                </li>
              </Steps>
              <p>
                Kết quả cần thấy: điểm làm việc có chính sách đang hiệu lực và
                nhân viên được phân công đúng điểm. Nếu bản đồ hoặc GPS báo lỗi,
                kiểm tra lại vị trí trước khi dùng dữ liệu chấm công.
              </p>
              <WorkspaceLink href="/admin/attendance/worksites">
                Mở điểm chấm công
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="employees"
              icon={UsersRound}
              title="Quản lý nhân viên và tính lương"
            >
              <p>
                Hồ sơ nhân viên và tài khoản đăng nhập là hai phần riêng. Liên
                kết tài khoản đã đăng ký hoặc mời nhân viên bằng email, sau đó
                mới tạo hồ sơ nhân sự.
              </p>
              <Steps>
                <li>
                  Tìm tài khoản theo email. Nếu chưa có, gửi lời mời và chờ nhân
                  viên xác minh email.
                </li>
                <li>
                  Liên kết tài khoản với hồ sơ nhân viên; nhập phòng ban, vị
                  trí, hợp đồng, thời gian thử việc và mức lương áp dụng.
                </li>
                <li>
                  Tạo kỳ lương theo điểm làm việc và tháng. Tính số liệu, rồi
                  đối chiếu ngày công, nghỉ phép, tăng ca và các khoản điều
                  chỉnh trước khi xác nhận.
                </li>
                <li>
                  Chỉ chọn <strong>Đánh dấu đã chi</strong> sau khi xác nhận
                  tiền đã được chuyển. Tải báo cáo để đối chiếu với chứng từ
                  thanh toán.
                </li>
              </Steps>
              <p>
                Kết quả cần thấy: nhân viên đã liên kết đúng tài khoản; kỳ lương
                chuyển sang trạng thái xác nhận sau khi kiểm tra số liệu. Thao
                tác đánh dấu đã chi chỉ ghi nhận nội bộ, không tự chuyển tiền
                qua ngân hàng.
              </p>
              <div className="flex flex-wrap gap-3">
                <WorkspaceLink href="/admin/employees">
                  Mở nhân viên
                </WorkspaceLink>
                <WorkspaceLink href="/admin/payroll">
                  Mở bảng lương
                </WorkspaceLink>
              </div>
            </GuideSection>

            <GuideSection
              id="records"
              icon={UsersRound}
              title="Quản lý hồ sơ và người dùng"
            >
              <p>
                Dùng trang <strong>Người dùng</strong> để tra cứu tài khoản và
                chủ hồ sơ. Khi hỗ trợ một trường hợp cụ thể, đối chiếu email và
                mã hồ sơ trước khi thao tác.
              </p>
              <Steps>
                <li>Tìm tài khoản bằng email hoặc thông tin được cung cấp.</li>
                <li>
                  Mở hồ sơ liên quan; kiểm tra trạng thái, phiên bản và tài liệu
                  cần xử lý.
                </li>
                <li>
                  Nếu thiếu thông tin, gửi yêu cầu bổ sung để người nộp tự cập
                  nhật hồ sơ.
                </li>
                <li>Nếu cần khóa tài khoản, ghi rõ căn cứ và lý do.</li>
              </Steps>
              <WorkspaceLink href="/admin/users">
                Mở danh sách người dùng
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="review"
              icon={ClipboardCheck}
              title="Tổ chức thẩm định hồ sơ"
            >
              <p>
                Quản trị viên phân công hồ sơ; người thẩm định đánh giá từng tài
                liệu theo loại đã khai báo và ghi rõ căn cứ cho kết luận.
              </p>
              <Steps>
                <li>Mở hàng đợi và phân công hồ sơ cho người phù hợp.</li>
                <li>
                  Kiểm tra tiến độ; bảo đảm kết luận áp dụng cho đúng phiên bản
                  tài liệu.
                </li>
                <li>
                  Đối chiếu kết luận, lý do cần bổ sung hoặc từ chối và ghi chú
                  trước khi hoàn tất quyết định.
                </li>
              </Steps>
              <WorkspaceLink href="/admin/reviews">
                Mở hàng đợi thẩm định
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="payment"
              icon={BadgeDollarSign}
              title="Tạo yêu cầu thanh toán"
            >
              <p>
                Chỉ tạo khoản phí sau khi hồ sơ đến giai đoạn được phép thu.
                Việc này ảnh hưởng trực tiếp đến số tiền người nộp nhìn thấy.
              </p>
              <Steps>
                <li>Chọn hồ sơ đủ điều kiện và kiểm tra mã hồ sơ.</li>
                <li>
                  Nhập số tiền theo biểu phí hiện hành, nội dung khoản phí và
                  hạn thanh toán.
                </li>
                <li>
                  Xem lại thông tin, gửi yêu cầu và theo dõi trạng thái thanh
                  toán trong hệ thống.
                </li>
                <li>
                  Nếu người nộp báo đã chuyển tiền mà trạng thái chưa cập nhật,
                  đối chiếu giao dịch trước khi xử lý; không tạo khoản thu
                  trùng.
                </li>
              </Steps>
              <p>
                Kết quả cần thấy: yêu cầu thanh toán xuất hiện trên đúng hồ sơ
                với số tiền và hạn thanh toán đã kiểm tra.
              </p>
              <WorkspaceLink href="/admin/payments">
                Mở quản lý tài chính
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="blockchain"
              icon={Signature}
              title="Ghi nhận hồ sơ trên blockchain"
            >
              <p>
                Thực hiện sau khi hồ sơ hoàn tất xét duyệt và các điều kiện
                thanh toán. Hệ thống chỉ công bố dấu vân tay số; không đưa tài
                liệu gốc lên blockchain.
              </p>
              <Steps>
                <li>Kiểm tra hồ sơ đã đủ điều kiện ghi nhận.</li>
                <li>Kết nối ví được cấp quyền và chọn mạng Polygon.</li>
                <li>Đối chiếu mã hồ sơ, phiên bản và dấu vân tay số.</li>
                <li>
                  Xác nhận trong ví và theo dõi trạng thái đến khi hiển thị
                  <strong> Đã ghi nhận</strong>. Nếu đang chờ, kiểm tra giao
                  dịch trước khi thử lại.
                </li>
              </Steps>
              <p>
                Kết quả cần thấy: trạng thái <strong>Đã ghi nhận</strong> và mã
                giao dịch tương ứng. Nếu ví hoặc mạng không đúng, dừng thao tác
                và chọn lại trước khi ký.
              </p>
              <WorkspaceLink href="/blockchain">
                Mở khu vực ghi nhận
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="publication"
              icon={FileText}
              title="Công bố nội dung"
            >
              <p>
                Nội dung công bố có thể được xem bởi mọi người. Kiểm tra riêng
                các trường công khai dù hồ sơ đã được duyệt và ghi nhận.
              </p>
              <Steps>
                <li>Chọn hồ sơ đã đủ điều kiện công bố.</li>
                <li>
                  Đọc lại tiêu đề, mô tả; kiểm tra hình đại diện, danh mục và
                  địa điểm hiển thị.
                </li>
                <li>Xem trước nội dung trên máy tính và điện thoại.</li>
                <li>
                  Chỉ công bố khi thông tin chính xác và không chứa dữ liệu
                  riêng tư; kiểm tra lại trang công khai sau khi lưu.
                </li>
              </Steps>
              <p>
                Kết quả cần thấy: trang chi tiết công khai hiển thị đúng nội
                dung đã duyệt. Nếu chưa xuất hiện, kiểm tra trạng thái công bố
                trước khi thao tác lại.
              </p>
              <WorkspaceLink href="/admin/content">
                Mở quản trị nội dung
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="staff"
              icon={ShieldCheck}
              title="Quản lý tài khoản nhân sự"
            >
              <p>
                Quyền sử dụng hệ thống khác với hồ sơ nhân viên. Chỉ cấp vai trò
                kiểm duyệt hoặc quản trị cho người có nhiệm vụ tương ứng.
              </p>
              <Steps>
                <li>Xác nhận email công việc và nhiệm vụ trước khi mời.</li>
                <li>Chọn đúng vai trò, chỉ cấp quyền cần cho nhiệm vụ.</li>
                <li>
                  Kiểm tra trạng thái kích hoạt; xem lại quyền khi nhiệm vụ thay
                  đổi.
                </li>
                <li>
                  Khi nhân sự rời nhiệm vụ, khóa tài khoản theo quy trình của tổ
                  chức và kiểm tra quyền đã được thu hồi.
                </li>
              </Steps>
              <WorkspaceLink href="/admin/staff">
                Mở tài khoản nhân sự
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="audit"
              icon={FileClock}
              title="Kiểm tra lịch sử và báo cáo"
            >
              <p>
                Dùng lịch sử hoạt động để xác định ai thao tác, vào lúc nào và
                trên đối tượng nào. Báo cáo giúp theo dõi khối lượng công việc.
              </p>
              <Steps>
                <li>
                  Lọc theo thời gian, người thực hiện hoặc loại hoạt động.
                </li>
                <li>Mở bản ghi liên quan để đối chiếu trước khi kết luận.</li>
                <li>
                  Ghi lại kết quả kiểm tra và cách xử lý theo quy trình nội bộ.
                </li>
              </Steps>
              <div className="flex flex-wrap gap-3">
                <WorkspaceLink href="/admin/audit">
                  Mở lịch sử hoạt động
                </WorkspaceLink>
                <WorkspaceLink href="/admin/reports">Mở báo cáo</WorkspaceLink>
              </div>
            </GuideSection>

            <GuideSection
              id="troubleshooting"
              icon={CircleAlert}
              title="Xử lý tình huống thường gặp"
            >
              <div className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)]">
                <details className="p-4" open>
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Không thấy hồ sơ cần xử lý
                  </summary>
                  <p className="mt-2">
                    Bỏ bộ lọc, kiểm tra trạng thái và người được phân công. Nếu
                    vẫn không thấy, tra mã hồ sơ và xác nhận người nộp đã gửi hồ
                    sơ thành công.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Thanh toán chưa cập nhật
                  </summary>
                  <p className="mt-2">
                    Tra mã hồ sơ và mã giao dịch, kiểm tra trạng thái tại khu
                    vực thanh toán. Chỉ xử lý tiếp sau khi đã đối chiếu kết quả;
                    tránh tạo khoản thu thứ hai.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Ví không kết nối hoặc ký không thành công
                  </summary>
                  <p className="mt-2">
                    Mở khóa ví, chọn tài khoản được cấp quyền và mạng Polygon.
                    Nếu đã xác nhận giao dịch trong ví, kiểm tra trạng thái trên
                    hệ thống trước khi thao tác lại.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Nội dung chưa xuất hiện trên trang công khai
                  </summary>
                  <p className="mt-2">
                    Kiểm tra trạng thái công bố và bản xem trước, sau đó mở
                    trang công khai để xác nhận. Hồ sơ được duyệt chưa tự động
                    xuất hiện trong thư viện.
                  </p>
                </details>
              </div>
            </GuideSection>
          </div>
        </div>
      </div>
    </RoleGate>
  );
}
