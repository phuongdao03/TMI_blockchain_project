import Link from "next/link";

const workflowSteps = [
  {
    number: "01",
    title: "Tạo và hoàn thiện hồ sơ",
    action:
      "Chọn loại hồ sơ, mô tả giá trị cần xác lập và thêm các tài liệu liên quan.",
    outcome:
      "Lưu được bản nháp, biết phần còn thiếu và chủ động hoàn thiện trước khi nộp.",
  },
  {
    number: "02",
    title: "Nộp để kiểm tra",
    action: "Gửi hồ sơ khi thông tin và tài liệu đã sẵn sàng.",
    outcome:
      "Nhận mã theo dõi và trạng thái rõ ràng cho từng lần nộp hoặc bổ sung.",
  },
  {
    number: "03",
    title: "Thẩm định & phản hồi",
    action: "Theo dõi cập nhật và phản hồi hoặc bổ sung khi có yêu cầu.",
    outcome:
      "Biết hồ sơ đang được xem xét, cần điều chỉnh hay đã đạt điều kiện tiếp theo.",
  },
  {
    number: "04",
    title: "Xác lập và công bố",
    action: "Kiểm tra lại thông tin được phép công bố sau khi hồ sơ hoàn tất.",
    outcome:
      "Nhận chứng thư và mã tra cứu khi hồ sơ đủ điều kiện theo quy trình.",
  },
] as const;

const accountPaths = [
  {
    title: "Tra cứu công khai",
    access: "Không cần tài khoản",
    detail:
      "Tìm tác phẩm, kiểm tra chứng thư và xem những thông tin đã được chủ thể cho phép công bố.",
    next: "Mở Thư viện hoặc nhập mã tại trang Tra cứu chứng thư.",
  },
  {
    title: "Gửi và theo dõi hồ sơ",
    access: "Cần tài khoản",
    detail:
      "Tạo hồ sơ, lưu bản nháp, gửi tài liệu và theo dõi mọi phản hồi tại một nơi.",
    next: "Đăng ký hoặc đăng nhập để bắt đầu hồ sơ của bạn.",
  },
] as const;

export const policySections = [
  {
    id: "terms",
    title: "Điều khoản sử dụng",
    summary:
      "Nền tảng cung cấp không gian để tạo, quản lý, thẩm định, công bố và tra cứu thông tin theo quy trình vận hành được công bố tại từng thời điểm.",
    details: [
      "Việc sử dụng nền tảng đồng nghĩa với việc bạn chấp thuận các điều khoản này và các hướng dẫn hiển thị trong từng chức năng.",
      "Nền tảng có thể từ chối, tạm dừng hoặc giới hạn xử lý đối với hồ sơ có dấu hiệu vi phạm điều khoản, quyền của bên thứ ba hoặc quy định áp dụng.",
    ],
  },
  {
    id: "accounts-and-dossiers",
    title: "Tài khoản và hồ sơ",
    summary:
      "Mỗi tài khoản phải được sử dụng bởi đúng chủ thể đăng ký; mọi thông tin và tài liệu gửi lên cần chính xác, hợp pháp và thuộc phạm vi quyền sử dụng của bạn.",
    details: [
      "Bạn có trách nhiệm bảo mật thông tin đăng nhập, cập nhật hồ sơ khi có thay đổi và phản hồi yêu cầu bổ sung trong thời hạn được thông báo.",
      "Việc gửi hồ sơ không đồng nghĩa với việc hồ sơ được chấp thuận, công bố hoặc cấp chứng thư.",
    ],
  },
  {
    id: "privacy",
    title: "Chính sách quyền riêng tư",
    summary:
      "Thông tin cá nhân, thông tin liên hệ, dữ liệu hồ sơ và tệp đính kèm chỉ được xử lý trong phạm vi cần thiết để vận hành tài khoản và giải quyết hồ sơ.",
    details: [
      "Dữ liệu không công khai được giới hạn theo vai trò, mục đích xử lý và các biện pháp bảo mật phù hợp với hệ thống.",
      "Bạn có thể yêu cầu xem xét, điều chỉnh hoặc cập nhật thông tin cá nhân của mình thông qua kênh hỗ trợ chính thức, trong phạm vi pháp luật và quy trình cho phép.",
    ],
  },
  {
    id: "publication-and-verification",
    title: "Công bố, kiểm chứng và chứng thư",
    summary:
      "Thông tin công khai chỉ được hiển thị sau khi hoàn tất các bước xử lý phù hợp; phạm vi hiển thị có thể thay đổi theo trạng thái, quyết định xử lý hoặc yêu cầu bảo vệ thông tin.",
    details: [
      "Mã tra cứu, QR và chứng thư phản ánh dữ liệu của bản ghi tại thời điểm xác minh trên hệ thống.",
      "Thông tin xác minh không thay thế việc tự đánh giá về quyền sở hữu, quyền tác giả, tính hợp pháp hoặc nghĩa vụ của các bên liên quan.",
    ],
  },
  {
    id: "rights-and-responsibilities",
    title: "Quyền, nghĩa vụ và giới hạn trách nhiệm",
    summary:
      "Bạn có quyền theo dõi trạng thái hồ sơ, nhận phản hồi và đề nghị xem xét khi phát hiện thông tin chưa chính xác; đồng thời phải sử dụng nền tảng một cách trung thực và đúng mục đích.",
    details: [
      "Không được mạo danh, cung cấp nội dung sai lệch, xâm phạm quyền của bên thứ ba hoặc can thiệp trái phép vào hệ thống.",
      "Nền tảng không chịu trách nhiệm đối với thiệt hại phát sinh từ thông tin do người dùng cung cấp không chính xác, việc sử dụng trái quy định hoặc các sự kiện nằm ngoài khả năng kiểm soát hợp lý.",
    ],
  },
  {
    id: "policy-updates",
    title: "Cập nhật chính sách",
    summary:
      "Điều khoản và chính sách có thể được điều chỉnh để phù hợp với thay đổi về vận hành, công nghệ hoặc quy định áp dụng.",
    details: [
      "Phiên bản đang có hiệu lực được công bố tại trang này; việc tiếp tục sử dụng nền tảng sau khi cập nhật được hiểu là bạn đã xem và chấp thuận phiên bản mới.",
      "Các thay đổi quan trọng có thể được thông báo trong tài khoản hoặc trên nền tảng trước khi áp dụng, khi phù hợp.",
    ],
  },
] as const;

export function ProcessGuide({ compact = false }: { compact?: boolean }) {
  const steps = compact ? workflowSteps.slice(0, 3) : workflowSteps;

  return (
    <section className="public-process-guide" id="process-details">
      <div className="public-information-shell">
        <header className="public-information-intro">
          <p className="public-information-kicker">QUY TRÌNH HỒ SƠ</p>
          <h2>Từ hồ sơ đến chứng thư, rõ ở từng mốc.</h2>
          <p>
            Bốn bước ngắn gọn để bạn chuẩn bị, gửi, theo dõi và tra cứu kết quả
            mà không phải đoán bước tiếp theo.
          </p>
          {compact ? (
            <Link className="public-information-link" href="/process">
              Xem toàn bộ quy trình
            </Link>
          ) : null}
        </header>
        <ol className="public-process-list">
          {steps.map((step) => (
            <li key={step.number}>
              <article className="public-process-step">
                <div className="public-process-step__heading">
                  <p aria-hidden="true" className="public-process-step__number">
                    {step.number}
                  </p>
                  <h3>{step.title}</h3>
                </div>
                <dl className="public-process-step__content">
                  <div>
                    <dt>Bạn thực hiện</dt>
                    <dd>{step.action}</dd>
                  </div>
                  <div>
                    <dt>Kết quả bạn nhận</dt>
                    <dd>{step.outcome}</dd>
                  </div>
                </dl>
              </article>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export function AccessGuide({ compact = false }: { compact?: boolean }) {
  const paths = compact ? accountPaths.slice(0, 2) : accountPaths;

  return (
    <section className="public-access-guide">
      <div className="public-information-shell">
        <div className="public-access-guide__intro">
          <p className="public-information-kicker">BẮT ĐẦU ĐÚNG CÁCH</p>
          <h2>Chọn việc bạn muốn làm.</h2>
        </div>
        <div className="public-access-guide__list">
          {paths.map(({ title, access, detail, next }) => (
            <article className="public-access-guide__item" key={title}>
              <div>
                <p>{access}</p>
                <h3>{title}</h3>
              </div>
              <div>
                <p>{detail}</p>
                <p>{next}</p>
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
    <section className="public-policy-guide">
      <div className="public-policy-shell">
        <nav aria-label="Mục lục chính sách" className="public-policy-index">
          <p>Trong trang này</p>
          <ol>
            {policySections.map(({ id, title }, index) => (
              <li key={id}>
                <a href={`#${id}`}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  {title}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div className="public-policy-list">
          {policySections.map(({ details, id, summary, title }, index) => (
            <article id={id} key={id}>
              <p aria-hidden="true">{String(index + 1).padStart(2, "0")}</p>
              <h2>{title}</h2>
              <p>{summary}</p>
              <ul>
                {details.map((detail) => (
                  <li key={detail}>{detail}</li>
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
