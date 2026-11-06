"use client";

import {
  Award,
  ClipboardList,
  CreditCard,
  FileText,
  SearchCheck,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

const steps = [
  {
    title: "Chuẩn bị hồ sơ",
    summary: "Điền thông tin và tập hợp tài liệu liên quan.",
    action:
      "Tạo hồ sơ, chọn loại đề cử phù hợp và điền thông tin về người, tác phẩm hoặc giá trị được đề cử.",
    prepare:
      "Chuẩn bị thông tin về người, tổ chức hoặc giá trị được đề cử cùng tài liệu liên quan. Danh mục cụ thể sẽ hiện theo loại hồ sơ bạn chọn.",
    next: "Bạn có thể lưu bản nháp và hoàn thiện hồ sơ trước khi gửi.",
    icon: FileText,
    illustration: "documents",
  },
  {
    title: "Gửi hồ sơ",
    summary: "Rà soát, gửi hồ sơ và thanh toán phí nếu được yêu cầu.",
    action:
      "Rà soát thông tin rồi gửi hồ sơ. Nếu hồ sơ cần phí nộp, khoản phí sẽ hiển thị để bạn thanh toán trước khi hồ sơ chuyển sang xem xét.",
    prepare:
      "Hoàn tất các mục bắt buộc và thêm tài liệu liên quan trước khi gửi.",
    next: "Sau khi gửi và hoàn tất phí nộp nếu được yêu cầu, hồ sơ chuyển sang bước kiểm tra ban đầu.",
    icon: CreditCard,
    illustration: "payment",
  },
  {
    title: "Xem xét hồ sơ",
    summary: "Theo dõi trạng thái và bổ sung khi được yêu cầu.",
    action:
      "Đăng nhập, mở hồ sơ của bạn để xem trạng thái và đọc phản hồi từ Trung tâm.",
    prepare:
      "Theo dõi thông báo trong tài khoản để không bỏ lỡ yêu cầu bổ sung.",
    next: "Nếu hồ sơ cần thêm thông tin, bạn có thể cập nhật phần được yêu cầu và gửi lại.",
    icon: SearchCheck,
    illustration: "review",
  },
  {
    title: "Nhận kết quả",
    summary: "Xem kết quả và tra cứu bằng xác lập nếu được cấp.",
    action:
      "Xem kết quả trong hồ sơ. Nếu hồ sơ đủ điều kiện, hãy theo dõi thông báo phát hành bằng xác lập.",
    prepare:
      "Giữ lại mã hồ sơ để thuận tiện khi theo dõi. Mã tra cứu bằng xác lập sẽ có khi bằng được phát hành.",
    next: "Bạn có thể tra cứu bằng xác lập và xem thông tin đã được phép công bố trên trang Tra cứu.",
    icon: Award,
    illustration: "certificate",
  },
] as const;

const commonQuestions = [
  {
    question: "Nếu hồ sơ còn thiếu giấy tờ thì sao?",
    answer:
      "Nếu chưa gửi, bạn có thể tiếp tục hoàn thiện bản nháp. Sau khi gửi, hãy theo dõi hồ sơ trong tài khoản; nếu Trung tâm yêu cầu bổ sung, phần cần bổ sung và hướng dẫn sẽ hiển thị tại đó.",
  },
  {
    question: "Tôi có thể sửa hồ sơ sau khi gửi không?",
    answer:
      "Hồ sơ đã gửi được khóa trong lúc xem xét. Khi có yêu cầu bổ sung, bạn có thể cập nhật phần được yêu cầu và gửi lại hồ sơ.",
  },
  {
    question: "Làm sao biết hồ sơ đang được xem xét?",
    answer:
      "Đăng nhập và mở mục Hồ sơ của tôi. Tại từng hồ sơ, bạn có thể xem trạng thái, tiến độ và phản hồi mới nhất.",
  },
  {
    question: "Nếu hồ sơ không được chấp nhận thì sao?",
    answer:
      "Bạn có thể xem kết quả và ghi chú thẩm định trong hồ sơ. Hãy đọc hướng dẫn đi kèm để biết việc cần làm tiếp theo; nếu cần giải thích thêm, bạn có thể liên hệ Trung tâm.",
  },
  {
    question: "Sau khi được xác lập, tôi có thể quảng bá hồ sơ không?",
    answer:
      "Bạn có thể theo dõi việc công bố thông thường mà không cần mua quảng cáo. Quảng bá là lựa chọn riêng và không phải điều kiện để công bố hồ sơ đã đủ điều kiện.",
  },
] as const;

function StepIllustration({ kind }: { kind: (typeof steps)[number]["illustration"] }) {
  return (
    <svg
      aria-hidden="true"
      className={`process-illustration process-illustration--${kind}`}
      fill="none"
      viewBox="0 0 320 240"
    >
      <circle className="process-illustration__orbit" cx="160" cy="120" r="92" />
      <circle className="process-illustration__orbit" cx="160" cy="120" r="76" />
      <circle className="process-illustration__sun" cx="246" cy="55" r="5" />
      <circle className="process-illustration__sun" cx="74" cy="181" r="3" />
      {kind === "documents" ? (
        <>
          <path className="process-illustration__shadow" d="M91 61h82l34 34v91H91z" />
          <path className="process-illustration__paper" d="M107 46h80l31 31v94h-111z" />
          <path className="process-illustration__fold" d="M187 46v32h31" />
          <path className="process-illustration__line" d="M128 101h66M128 119h66M128 137h47" />
          <path className="process-illustration__accent" d="m119 163 8 8 16-18" />
        </>
      ) : null}
      {kind === "payment" ? (
        <>
          <rect className="process-illustration__paper" height="105" rx="9" width="147" x="86" y="74" />
          <path className="process-illustration__accent" d="M87 102h145" />
          <path className="process-illustration__line" d="M108 132h44m-44 17h27" />
          <circle className="process-illustration__medal" cx="195" cy="151" r="23" />
          <path className="process-illustration__accent" d="m188 151 5 5 10-12" />
        </>
      ) : null}
      {kind === "review" ? (
        <>
          <path className="process-illustration__paper" d="M95 61h101l25 25v99H95z" />
          <path className="process-illustration__fold" d="M196 61v26h25" />
          <path className="process-illustration__line" d="M116 105h73m-73 17h53m-53 17h41" />
          <circle className="process-illustration__lens" cx="190" cy="151" r="26" />
          <path className="process-illustration__accent" d="m209 170 21 21" />
          <path className="process-illustration__accent" d="m180 151 7 7 14-16" />
        </>
      ) : null}
      {kind === "certificate" ? (
        <>
          <path className="process-illustration__paper" d="M92 49h136v126H92z" />
          <path className="process-illustration__ornament" d="M105 62h110v100H105z" />
          <path className="process-illustration__accent" d="M126 88h68m-56 15h44" />
          <circle className="process-illustration__medal" cx="160" cy="145" r="21" />
          <path className="process-illustration__accent" d="m151 145 6 6 12-14" />
          <path className="process-illustration__ribbon" d="m146 163-5 24 19-10 19 10-5-24" />
        </>
      ) : null}
    </svg>
  );
}

export function ProcessJourney({ submissionOpen = true }: { submissionOpen?: boolean }) {
  const [activeStep, setActiveStep] = useState(0);
  const [journeyEntered, setJourneyEntered] = useState(false);
  const stepsRef = useRef<HTMLOListElement>(null);
  const selected = steps[activeStep]!;
  const StepIcon = selected.icon;

  useEffect(() => {
    const node = stepsRef.current;
    if (!node || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setJourneyEntered(true);
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.15 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <>
      <section
        aria-labelledby="process-journey-title"
        className="process-journey"
        id="process-details"
      >
        <div className="process-journey__inner">
          <header className="process-journey__intro">
            <p className="public-information-kicker">4 BƯỚC ĐỀ CỬ</p>
            <h2 id="process-journey-title">Từng bước, bạn sẽ biết mình cần làm gì.</h2>
            <p>
              Chọn một bước để xem việc cần làm, tài liệu cần chuẩn bị và điều sẽ xảy ra tiếp theo.
            </p>
          </header>

          <ol
            aria-label="Các bước gửi hồ sơ"
            className={`process-journey__steps${journeyEntered ? " process-journey__steps--visible" : ""}`}
            ref={stepsRef}
          >
            {steps.map(({ icon: Icon, summary, title }, index) => (
              <li key={title}>
                <button
                  aria-controls="process-step-detail"
                  aria-pressed={activeStep === index}
                  className="process-journey__step"
                  onClick={() => setActiveStep(index)}
                  type="button"
                >
                  <span aria-hidden="true" className="process-journey__step-icon">
                    <Icon className="size-5" strokeWidth={1.8} />
                  </span>
                  <span className="process-journey__step-copy">
                    <span className="process-journey__step-number">
                      Bước {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="process-journey__step-title">{title}</span>
                    <span className="process-journey__step-summary">{summary}</span>
                  </span>
                </button>
              </li>
            ))}
          </ol>

          <section
            aria-atomic="true"
            aria-labelledby="process-step-detail-title"
            aria-live="polite"
            className="process-step-detail"
            id="process-step-detail"
            role="region"
          >
            <div className="process-step-detail__copy">
              <p className="process-step-detail__eyebrow">
                <span aria-hidden="true" className="process-step-detail__selected-icon">
                  <StepIcon className="size-4" strokeWidth={1.8} />
                </span>
                <span>BƯỚC {String(activeStep + 1).padStart(2, "0")} / 04</span>
              </p>
              <h3 id="process-step-detail-title">{selected.title}</h3>
              <dl className="process-step-detail__facts">
                <div>
                  <dt>Bạn cần làm gì?</dt>
                  <dd>
                    {activeStep === 1 && !submissionOpen
                      ? "Khi cổng gửi hồ sơ mở, hãy rà soát thông tin rồi gửi hồ sơ. Nếu hồ sơ cần phí nộp, khoản phí sẽ hiển thị để bạn thanh toán trước khi hồ sơ chuyển sang xem xét."
                      : selected.action}
                  </dd>
                </div>
                <div>
                  <dt>Cần chuẩn bị gì?</dt>
                  <dd>{selected.prepare}</dd>
                </div>
                <div>
                  <dt>Sau đó thì sao?</dt>
                  <dd>
                    {activeStep === 1 && !submissionOpen
                      ? "Khi cổng gửi hồ sơ mở, bạn sẽ thấy các yêu cầu và khoản phí áp dụng trước khi xác nhận."
                      : selected.next}
                  </dd>
                </div>
              </dl>
            </div>
            <div className="process-step-detail__art">
              <StepIllustration kind={selected.illustration} />
              <p>
                <ClipboardList aria-hidden="true" className="size-4" />
                Gửi đề cử không bảo đảm hồ sơ sẽ được xác lập.
              </p>
            </div>
          </section>
        </div>
      </section>

      <section aria-labelledby="process-faq-title" className="process-faq">
        <div className="process-faq__inner">
          <header className="process-faq__intro">
            <p className="public-information-kicker">CÂU HỎI THƯỜNG GẶP</p>
            <h2 id="process-faq-title">Khi cần thêm thông tin</h2>
            <p>Câu trả lời ngắn gọn cho những tình huống thường gặp khi gửi hồ sơ.</p>
          </header>
          <div className="process-faq__list">
            {commonQuestions.map(({ answer, question }) => (
              <details className="process-faq__item" key={question}>
                <summary>
                  <span>{question}</span>
                  <span aria-hidden="true" className="process-faq__toggle">+</span>
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
