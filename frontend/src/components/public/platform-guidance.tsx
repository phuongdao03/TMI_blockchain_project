import Link from "next/link";

import { ProcessStep } from "@/components/ui/process-step";

const workflowSteps = [
  {
    number: "01",
    title: "Xác định nhu cầu",
    userAction:
      "Chọn tra cứu chứng thư có sẵn hoặc bắt đầu một hồ sơ mới cho tác phẩm của bạn.",
    tmiAction:
      "TMI hướng dẫn đúng điểm bắt đầu và cho biết trước những thông tin cần chuẩn bị.",
    result:
      "Bạn có lộ trình rõ ràng, không phải điền thông tin khi chưa biết mục đích sử dụng.",
  },
  {
    number: "02",
    title: "Chuẩn bị hồ sơ",
    userAction:
      "Cung cấp thông tin tác phẩm, chủ thể liên quan và tải lên tài liệu chứng minh.",
    tmiAction:
      "TMI kiểm tra các mục bắt buộc, định dạng tệp và thông báo ngay phần còn thiếu.",
    result:
      "Hồ sơ có mã theo dõi và danh sách tài liệu cần hoàn thiện trước khi gửi.",
  },
  {
    number: "03",
    title: "Gửi và bổ sung tài liệu",
    userAction:
      "Xác nhận thông tin, gửi hồ sơ và phản hồi yêu cầu bổ sung nếu có.",
    tmiAction:
      "TMI tiếp nhận, kiểm tra tính đầy đủ và cập nhật tiến độ bằng ngôn ngữ dễ hiểu.",
    result:
      "Bạn biết hồ sơ đang chờ kiểm tra, cần bổ sung hay đã sẵn sàng để thẩm định.",
  },
  {
    number: "04",
    title: "Thẩm định",
    userAction:
      "Theo dõi tiến độ và chỉ cung cấp thêm thông tin khi nhận được yêu cầu cụ thể.",
    tmiAction:
      "TMI tổ chức đánh giá độc lập, kiểm soát xung đột lợi ích và tổng hợp kết quả.",
    result:
      "Bạn nhận được kết luận rõ ràng: đạt yêu cầu, cần bổ sung hoặc chưa đủ điều kiện.",
  },
  {
    number: "05",
    title: "Thanh toán và nhận chứng thư",
    userAction:
      "Thanh toán phí phát hành khi hồ sơ đủ điều kiện, sau đó kiểm tra thông tin trước khi nhận.",
    tmiAction:
      "TMI đối soát khoản thanh toán, phát hành chứng thư và mở trang kiểm tra công khai.",
    result:
      "Bạn có chứng thư để tải xuống và đường dẫn xác minh có thể chia sẻ độc lập.",
  },
] as const;

const accountPaths = [
  {
    title: "Tra cứu công khai",
    access: "Không cần tài khoản",
    detail:
      "Tìm tác phẩm, kiểm tra chứng thư và xem thông tin đã được chủ thể cho phép công bố.",
    next: "Mở Thư viện hoặc nhập mã tại trang Xác minh.",
  },
  {
    title: "Gửi hồ sơ",
    access: "Tự tạo tài khoản",
    detail:
      "Cá nhân và tổ chức có thể đăng ký để chuẩn bị hồ sơ, nhận thông báo và tải chứng thư.",
    next: "Đăng ký, xác nhận email rồi bắt đầu hồ sơ đầu tiên.",
  },
  {
    title: "Làm việc nội bộ",
    access: "Chỉ qua lời mời",
    detail:
      "Nhân sự tham gia kiểm tra và phê duyệt nhận tài khoản theo nhiệm vụ được giao.",
    next: "Mở liên kết trong email mời và hoàn tất bước bảo vệ tài khoản.",
  },
] as const;

export const policySections = [
  {
    id: "data-collected",
    title: "Dữ liệu được thu thập",
    summary:
      "TMI chỉ thu thập thông tin cần để tạo tài khoản, xử lý hồ sơ, hỗ trợ thanh toán và phát hành chứng thư.",
    details: [
      "Thông tin liên hệ và thông tin đại diện của cá nhân hoặc tổ chức.",
      "Nội dung hồ sơ, tài liệu chứng minh và lịch sử bổ sung do bạn cung cấp.",
      "Thông tin giao dịch cần để xác nhận khoản phí; TMI không yêu cầu bạn gửi thông tin đăng nhập ngân hàng.",
    ],
  },
  {
    id: "account-protection",
    title: "Cách bảo vệ tài khoản",
    summary:
      "Tài khoản được bảo vệ bằng xác minh danh tính, giới hạn đăng nhập bất thường và khả năng thu hồi quyền truy cập.",
    details: [
      "Không chia sẻ mật khẩu, mã xác nhận hoặc liên kết lời mời cho người khác.",
      "Bạn có thể yêu cầu đặt lại mật khẩu khi mất quyền truy cập.",
      "Nhân sự nội bộ phải hoàn tất bước bảo vệ tăng cường trước khi xử lý công việc.",
    ],
  },
  {
    id: "dossier-evidence",
    title: "Cách xử lý hồ sơ và bằng chứng",
    summary:
      "Tài liệu chỉ được dùng để kiểm tra hồ sơ, giải quyết yêu cầu liên quan và chứng minh kết quả đã phát hành.",
    details: [
      "Tệp gốc và ghi chú xử lý không xuất hiện trên trang công khai.",
      "Chỉ người đang phụ trách công việc mới được xem phần thông tin cần thiết.",
      "Thông tin công khai được giới hạn theo nội dung đã được duyệt để công bố.",
    ],
  },
  {
    id: "retention",
    title: "Thời gian lưu trữ",
    summary:
      "Thông tin được lưu trong thời gian cần thiết để xử lý hồ sơ, duy trì khả năng xác minh và đáp ứng nghĩa vụ áp dụng.",
    details: [
      "Bản nháp chưa gửi có thể được xóa theo yêu cầu của chủ tài khoản.",
      "Hồ sơ đã phát hành cần giữ các thông tin tối thiểu để chứng thư tiếp tục được kiểm tra.",
      "Khi hết mục đích lưu trữ, dữ liệu được xóa hoặc chuyển thành dạng không còn nhận diện cá nhân.",
    ],
  },
  {
    id: "user-rights",
    title: "Quyền của người dùng",
    summary:
      "Bạn có thể xem, sửa thông tin chưa khóa, tải dữ liệu phù hợp và yêu cầu giải thích về việc xử lý hồ sơ.",
    details: [
      "Yêu cầu chỉnh sửa thông tin sai hoặc bổ sung thông tin còn thiếu.",
      "Yêu cầu hạn chế công bố trong phạm vi không ảnh hưởng đến tính xác thực của chứng thư.",
      "Yêu cầu đóng tài khoản khi không còn hồ sơ hoặc nghĩa vụ cần duy trì.",
    ],
  },
  {
    id: "complaints",
    title: "Quy trình xử lý khiếu nại",
    summary:
      "Khiếu nại được tiếp nhận theo mã hồ sơ, xác nhận thời điểm nhận và chuyển đến người phụ trách phù hợp.",
    details: [
      "Nêu rõ mã hồ sơ, nội dung cần xem xét và tài liệu liên quan.",
      "TMI thông báo đã tiếp nhận và cập nhật khi cần thêm thông tin.",
      "Kết quả phản hồi nêu quyết định, căn cứ và cách yêu cầu xem xét tiếp theo.",
    ],
  },
  {
    id: "staff-invitations",
    title: "Cách cấp tài khoản nhân sự nội bộ",
    summary:
      "Tài khoản nội bộ không được tự đăng ký. Người phụ trách chỉ gửi lời mời sau khi xác minh nhu cầu công việc.",
    details: [
      "Lời mời được gửi đến email công việc, có thời hạn và chỉ dùng một lần.",
      "Phạm vi công việc được xác định trước và có thể điều chỉnh hoặc thu hồi.",
      "Khi nhiệm vụ kết thúc, quyền truy cập được đóng nhưng kết quả công việc đã ghi nhận vẫn được giữ để đối chiếu.",
    ],
  },
] as const;

export function ProcessGuide({ compact = false }: { compact?: boolean }) {
  const steps = compact ? workflowSteps.slice(0, 3) : workflowSteps;
  return (
    <section className="bg-[#fbf7f0] text-neutral-950" id="process-details">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:gap-20">
          <div className="lg:sticky lg:top-28 lg:self-start">
            <p className="text-xs font-semibold tracking-[0.16em] text-primary-700 uppercase">
              Quy trình từng bước
            </p>
            <h2 className="mt-4 max-w-md text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
              Biết việc cần làm và kết quả ở từng mốc.
            </h2>
            <p className="mt-5 max-w-md text-base leading-7 text-neutral-700">
              Mỗi bước dưới đây trả lời ba câu hỏi: bạn chuẩn bị gì, TMI xử lý
              gì và bạn nhận được kết quả nào.
            </p>
            {compact ? (
              <Link
                className="mt-7 inline-flex min-h-11 items-center border-b-2 border-primary-600 text-sm font-semibold text-primary-700"
                href="/process"
              >
                Xem toàn bộ quy trình
              </Link>
            ) : null}
          </div>
          <ol>
            {steps.map((step) => (
              <li key={step.number}>
                <ProcessStep number={step.number} title={step.title}>
                  <dl className="grid gap-5 sm:grid-cols-3">
                    <div>
                      <dt className="font-semibold text-neutral-950">
                        Bạn cần làm gì?
                      </dt>
                      <dd className="mt-1">{step.userAction}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-neutral-950">
                        TMI xử lý gì?
                      </dt>
                      <dd className="mt-1">{step.tmiAction}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold text-neutral-950">
                        Bạn nhận được gì?
                      </dt>
                      <dd className="mt-1">{step.result}</dd>
                    </div>
                  </dl>
                </ProcessStep>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

export function AccessGuide({ compact = false }: { compact?: boolean }) {
  const paths = compact ? accountPaths.slice(0, 2) : accountPaths;
  return (
    <section className="border-t border-neutral-200 bg-[#f5efe5] text-neutral-950">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8 lg:py-24">
        <div className="max-w-2xl">
          <p className="text-xs font-semibold tracking-[0.16em] text-primary-700 uppercase">
            Cách bắt đầu
          </p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Chọn theo việc bạn muốn hoàn thành.
          </h2>
        </div>
        <div className="mt-10 divide-y divide-neutral-300 border-y border-neutral-300">
          {paths.map(({ title, access, detail, next }) => (
            <article
              className="grid gap-4 py-7 sm:grid-cols-[12rem_1fr]"
              key={title}
            >
              <div>
                <p className="text-xs font-semibold text-primary-700">
                  {access}
                </p>
                <h3 className="mt-1 text-xl font-semibold">{title}</h3>
              </div>
              <div className="max-w-2xl text-sm leading-7 text-neutral-700">
                <p>{detail}</p>
                <p className="mt-2 font-medium text-neutral-950">{next}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function PolicyGuide() {
  return (
    <section className="bg-[#fbf7f0] text-neutral-950">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[15rem_1fr] lg:px-8 lg:py-24">
        <nav
          aria-label="Mục lục chính sách"
          className="lg:sticky lg:top-28 lg:self-start"
        >
          <p className="text-sm font-semibold">Trong trang này</p>
          <ol className="mt-4 grid gap-1 border-l border-neutral-300">
            {policySections.map(({ id, title }, index) => (
              <li key={id}>
                <a
                  className="block min-h-11 py-2 pl-4 text-sm leading-6 text-neutral-600 hover:border-primary-600 hover:text-primary-700 focus-visible:text-primary-700"
                  href={`#${id}`}
                >
                  {String(index + 1).padStart(2, "0")}. {title}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="divide-y divide-neutral-300 border-y border-neutral-300">
          {policySections.map(({ details, id, summary, title }, index) => (
            <article className="scroll-mt-28 py-9" id={id} key={id}>
              <p className="font-mono text-xs font-semibold text-primary-700">
                {String(index + 1).padStart(2, "0")}
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                {title}
              </h2>
              <p className="mt-4 max-w-3xl text-base leading-7 text-neutral-700">
                {summary}
              </p>
              <ul className="mt-5 grid gap-3 text-sm leading-7 text-neutral-700">
                {details.map((detail) => (
                  <li className="grid grid-cols-[1rem_1fr] gap-2" key={detail}>
                    <span aria-hidden="true" className="text-primary-700">
                      —
                    </span>
                    <span>{detail}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

export function SecurityPolicy() {
  return <PolicyGuide />;
}

export function RoleProvisioningPolicy() {
  const invitation = policySections.find(
    ({ id }) => id === "staff-invitations",
  );
  if (!invitation) return null;
  return (
    <section className="border-t border-neutral-200 bg-[#f5efe5] px-4 py-16 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-3xl">
        <h2 className="text-2xl font-semibold">{invitation.title}</h2>
        <p className="mt-4 leading-7 text-neutral-700">{invitation.summary}</p>
      </div>
    </section>
  );
}

export function PlatformGuidance() {
  return (
    <>
      <ProcessGuide compact />
      <AccessGuide compact />
    </>
  );
}
