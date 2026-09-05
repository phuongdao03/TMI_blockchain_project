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
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-[var(--theme-text)] sm:text-5xl">
            Hướng dẫn quản trị
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--theme-muted)] sm:text-base">
            Hướng dẫn các công việc vận hành thường ngày, từ tiếp nhận hồ sơ đến
            công bố kết quả. Mỗi phần cho biết nơi thao tác, thứ tự thực hiện và
            điểm cần kiểm tra trước khi xác nhận.
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
                Mở <strong>Tổng quan vận hành</strong> để nắm hồ sơ đang chờ,
                khoản thanh toán, nội dung sắp công bố và các cảnh báo cần xử
                lý. Ưu tiên công việc quá hạn hoặc có trạng thái lỗi trước.
              </p>
              <Steps>
                <li>Kiểm tra thông báo mới và các việc đang quá hạn.</li>
                <li>Mở từng nhóm công việc để xác nhận dữ liệu thực tế.</li>
                <li>
                  Chỉ thực hiện hành động khi tài khoản của bạn có đúng quyền.
                </li>
              </Steps>
              <WorkspaceLink href="/admin/dashboard">
                Mở tổng quan vận hành
              </WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="records"
              icon={UsersRound}
              title="Quản lý hồ sơ và người dùng"
            >
              <p>
                Trang <strong>Người dùng</strong> dùng để tra cứu chủ hồ sơ và
                tình trạng tài khoản. Khi cần hỗ trợ, hãy đối chiếu đúng email,
                mã hồ sơ và phiên bản trước khi cập nhật trạng thái.
              </p>
              <Steps>
                <li>Tìm người dùng bằng thông tin nhận diện có sẵn.</li>
                <li>
                  Mở hồ sơ liên quan và kiểm tra tài liệu theo từng loại đã khai
                  báo.
                </li>
                <li>
                  Không sửa nội dung thay cho người nộp; yêu cầu họ bổ sung khi
                  thiếu.
                </li>
                <li>Khóa tài khoản chỉ khi có căn cứ và ghi rõ lý do.</li>
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
                Mỗi hồ sơ có thể chứa nhiều tài liệu khác loại. Nhân viên thẩm
                định kiểm tra từng tài liệu theo loại mà người nộp đã chọn, ghi
                nhận đạt, cần bổ sung hoặc không phù hợp và nêu căn cứ rõ ràng.
              </p>
              <Steps>
                <li>Phân công hồ sơ cho người có chuyên môn phù hợp.</li>
                <li>
                  Đảm bảo người thẩm định đang xem đúng phiên bản tài liệu.
                </li>
                <li>
                  Kiểm tra kết luận, căn cứ và ghi chú trước khi hoàn tất phiếu
                  thẩm định.
                </li>
              </Steps>
              <WorkspaceLink href="/reviews">Mở hồ sơ đánh giá</WorkspaceLink>
            </GuideSection>

            <GuideSection
              id="payment"
              icon={BadgeDollarSign}
              title="Tạo yêu cầu thanh toán"
            >
              <p>
                Chỉ tạo khoản phí sau khi hồ sơ đã đến đúng giai đoạn thu phí.
                Kiểm tra mã hồ sơ, số tiền, nội dung khoản phí và hạn thanh toán
                trước khi gửi cho người nộp.
              </p>
              <Steps>
                <li>
                  Chọn đúng hồ sơ đã được phê duyệt hoặc đủ điều kiện thu phí.
                </li>
                <li>
                  Nhập số tiền theo biểu phí đang áp dụng và mô tả dễ hiểu.
                </li>
                <li>
                  Gửi yêu cầu rồi theo dõi trạng thái thanh toán trong hệ thống.
                </li>
                <li>
                  Nếu tiền đã chuyển nhưng chưa cập nhật, chưa tạo yêu cầu
                  trùng.
                </li>
              </Steps>
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
                Bước này dành cho hồ sơ đã hoàn tất xét duyệt. Hệ thống chỉ công
                bố dấu vân tay số để kiểm tra tính toàn vẹn; không đưa tài liệu
                gốc lên blockchain.
              </p>
              <Steps>
                <li>Kết nối đúng ví của tổ chức và chọn mạng Polygon.</li>
                <li>Đối chiếu tên hồ sơ, phiên bản và dấu vân tay số.</li>
                <li>
                  Xác nhận giao dịch trong ví và chờ hệ thống báo đã ghi nhận.
                </li>
                <li>
                  Không đóng trang khi giao dịch đang chờ; không gửi lại cùng hồ
                  sơ.
                </li>
              </Steps>
              <p>
                Chỉ xem là hoàn tất khi trạng thái hiển thị{" "}
                <strong>Đã ghi nhận</strong>. Nếu ví hoặc mạng không đúng, dừng
                thao tác và chọn lại trước khi ký.
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
                Khu vực này quyết định nội dung nào xuất hiện trên trang công
                khai. Việc hồ sơ được duyệt hoặc đã ghi nhận blockchain không tự
                động đồng nghĩa với việc toàn bộ tài liệu được công khai.
              </p>
              <Steps>
                <li>Chọn tác phẩm hoặc hồ sơ đã đủ điều kiện công bố.</li>
                <li>
                  Kiểm tra tiêu đề, mô tả, hình đại diện, danh mục và địa điểm.
                </li>
                <li>Xem trước nội dung ở cả màn hình lớn và điện thoại.</li>
                <li>
                  Chọn công khai khi thông tin đã đúng và không lộ dữ liệu riêng
                  tư.
                </li>
              </Steps>
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
                Mời nhân sự bằng email công việc và cấp đúng vai trò cần dùng.
                Tài khoản chỉ được kích hoạt khi người được mời xác minh đúng
                email.
              </p>
              <Steps>
                <li>Kiểm tra email và nhiệm vụ trước khi gửi lời mời.</li>
                <li>Chỉ cấp các quyền cần thiết cho công việc được giao.</li>
                <li>
                  Khi đổi vai trò quan trọng, thực hiện đủ bước phê duyệt nội
                  bộ.
                </li>
                <li>
                  Khóa tài khoản ngay khi nhân sự không còn nhiệm vụ trong hệ
                  thống.
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
                Lịch sử hoạt động giúp đối chiếu ai đã thực hiện thao tác, vào
                thời điểm nào và trên đối tượng nào. Báo cáo dùng để theo dõi
                khối lượng công việc và phát hiện điểm bất thường.
              </p>
              <Steps>
                <li>
                  Lọc theo thời gian, người thực hiện hoặc loại hoạt động.
                </li>
                <li>Đối chiếu lịch sử trước khi kết luận có thao tác sai.</li>
                <li>
                  Không chỉnh sửa dữ liệu để che giấu sai sót; ghi nhận hướng xử
                  lý.
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
                    Kiểm tra bộ lọc, trạng thái và người được phân công. Nếu vẫn
                    không thấy, xác nhận hồ sơ đã được gửi chứ không còn là bản
                    nháp.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Thanh toán chưa cập nhật
                  </summary>
                  <p className="mt-2">
                    Đối chiếu mã hồ sơ và mã thanh toán. Chờ hệ thống nhận kết
                    quả trước khi tạo khoản thu mới hoặc xác nhận thủ công.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Ví không kết nối hoặc ký không thành công
                  </summary>
                  <p className="mt-2">
                    Mở khóa ví, chọn đúng tài khoản của tổ chức và mạng Polygon.
                    Nếu giao dịch đã gửi, kiểm tra trạng thái trước khi thử lại.
                  </p>
                </details>
                <details className="p-4">
                  <summary className="cursor-pointer font-semibold text-[var(--theme-text)]">
                    Nội dung chưa xuất hiện trên trang công khai
                  </summary>
                  <p className="mt-2">
                    Kiểm tra trạng thái công bố, thời điểm hiển thị và bản xem
                    trước. Hồ sơ được duyệt không tự động xuất hiện công khai.
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
