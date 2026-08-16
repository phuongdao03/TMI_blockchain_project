import Link from "next/link";

import { ProcessStep } from "@/components/ui/process-step";

const workflowSteps = [
  {
    number: "01",
    title: "Khám phá chương trình",
    userAction:
      "Xem các đề cử đã công bố, tiêu chí tham gia và những câu chuyện nổi bật.",
    tmiAction:
      "Nội dung được sắp xếp để bạn dễ tìm hiểu và đối chiếu thông tin được phép công khai.",
    result:
      "Bạn hiểu chương trình, đối tượng phù hợp và những thông tin nên chuẩn bị.",
  },
  {
    number: "02",
    title: "Chuẩn bị đề cử",
    userAction:
      "Tham khảo hướng dẫn và chuẩn bị câu chuyện, hình ảnh cùng tài liệu liên quan.",
    tmiAction:
      "Tiêu chí và danh mục tài liệu sẽ được công bố đầy đủ trước khi cổng tiếp nhận mở.",
    result: "Bạn chủ động chuẩn bị nội dung mà chưa cần tải tệp lên.",
  },
  {
    number: "03",
    title: "Gửi đề cử",
    userAction:
      "Khi cổng tiếp nhận mở, đăng nhập, điền thông tin và gửi tài liệu được yêu cầu.",
    tmiAction:
      "Hệ thống hướng dẫn theo từng bước và thông báo rõ nội dung còn thiếu trước khi gửi.",
    result:
      "Đề cử được ghi nhận với mã theo dõi để bạn có thể quay lại kiểm tra tiến trình.",
  },
  {
    number: "04",
    title: "Theo dõi tiến trình",
    userAction:
      "Theo dõi cập nhật và bổ sung thông tin khi có yêu cầu trong tài khoản của bạn.",
    tmiAction:
      "Đề cử được xem xét theo tiêu chí đã công bố; các cập nhật quan trọng được gửi tới bạn.",
    result:
      "Bạn biết đề cử đang được tiếp nhận, cần bổ sung hay đã hoàn tất xem xét.",
  },
  {
    number: "05",
    title: "Nhận kết quả",
    userAction:
      "Xem thông báo kết quả và kiểm tra lại phần thông tin được phép công bố.",
    tmiAction:
      "Kết quả được hoàn thiện và công bố theo phạm vi phù hợp của chương trình.",
    result:
      "Bạn nhận được hướng dẫn tiếp theo và đường dẫn chia sẻ nếu đề cử được công bố.",
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
    title: "Chuẩn bị gửi đề cử",
    access: "Sắp ra mắt",
    detail:
      "Bạn có thể xem trước quy trình và chuẩn bị nội dung ngay từ bây giờ. Website chưa yêu cầu tải tài liệu khi cổng tiếp nhận chưa mở.",
    next: "Khi tính năng được công bố, tài khoản hiện tại của bạn sẽ có hướng dẫn bắt đầu rõ ràng.",
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
      "Không chia sẻ mật khẩu, mã xác nhận hoặc đường dẫn truy cập riêng cho người khác.",
      "Bạn có thể yêu cầu đặt lại mật khẩu khi mất quyền truy cập.",
      "Một số thao tác nhạy cảm có thể yêu cầu thêm bước xác nhận để bảo vệ tài khoản.",
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
              Mỗi bước cho biết bạn cần chuẩn bị gì, điều gì sẽ diễn ra tiếp
              theo và kết quả bạn có thể nhận được.
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
                        Điều gì diễn ra tiếp theo?
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
            Bắt đầu từ việc bạn muốn làm.
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

export function PlatformGuidance() {
  return (
    <>
      <ProcessGuide compact />
      <AccessGuide compact />
    </>
  );
}
