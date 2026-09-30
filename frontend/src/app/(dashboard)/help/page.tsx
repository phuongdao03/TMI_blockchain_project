"use client";

import {
  BookOpenCheck,
  ClipboardCheck,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { useAuthUser } from "@/lib/auth/user-context";
import { resolveWorkspacePersona } from "@/lib/auth/role-workspaces";

type GuideTask = {
  id: string;
  title: string;
  steps: string[];
  result: string;
  problem?: string;
  href: string;
  action: string;
};

const reviewerTasks: GuideTask[] = [
  {
    id: "invitation",
    title: "Nhận quyền kiểm duyệt",
    steps: [
      "Mở Thông báo bằng đúng tài khoản có email được quản trị viên chọn.",
      "Tìm lời mời Người kiểm duyệt và bấm Chấp nhận. Nếu lời mời hết hạn, đề nghị quản trị viên gửi lại.",
      "Mở Công việc được giao. Tài khoản đã có quyền nhưng chưa thấy hồ sơ thì chờ quản trị viên phân công; không cần đăng ký tài khoản mới.",
    ],
    result:
      "Menu Công việc được giao và Hàng đợi thẩm định xuất hiện sau khi nhận quyền.",
    href: "/notifications",
    action: "Mở thông báo",
  },
  {
    id: "review",
    title: "Xử lý hồ sơ được phân công",
    steps: [
      "Mở Công việc được giao và chọn hồ sơ thẩm định; các phân công cũ và đầu việc mới đều hiển thị tại đây.",
      "Đối chiếu mã hồ sơ, phiên bản tài liệu và hạn xử lý trước khi đánh giá.",
      "Đọc từng tài liệu, ghi nhận phát hiện và căn cứ; lưu bản nháp khi chưa hoàn tất.",
      "Kiểm tra lại toàn bộ nhận xét rồi gửi kết quả. Nếu có xung đột lợi ích, khai báo trước khi tiếp tục.",
    ],
    result:
      "Trạng thái phiếu chuyển sang Đã gửi kết quả; quản trị viên nhận được kết luận để quyết định.",
    problem:
      "Nếu danh sách trống, quản trị viên cần phân công đúng tài khoản email này tại mục Phân công hồ sơ.",
    href: "/work-allocations",
    action: "Mở công việc được giao",
  },
  {
    id: "employee",
    title: "Chấm công và yêu cầu nhân sự",
    steps: [
      "Kiểm tra tài khoản đã được liên kết với hồ sơ nhân viên trong mục Nhân sự.",
      "Chờ quản trị viên gán điểm làm việc và lịch có hiệu lực. Mở Chấm công tại văn phòng, bật vị trí trên thiết bị rồi bấm ghi nhận giờ vào hoặc giờ ra.",
      "Kiểm tra sai số GPS và kết quả ghi nhận. Nếu vị trí không khả dụng, thử lại hoặc gửi yêu cầu ngoại lệ theo hướng dẫn trên màn hình.",
      "Gửi yêu cầu Nghỉ phép hoặc Tăng ca khi cần, rồi theo dõi trạng thái phê duyệt.",
    ],
    result: "Giờ vào/ra hoặc yêu cầu xuất hiện trong lịch sử cá nhân.",
    problem:
      "Nếu báo Chưa liên kết hồ sơ nhân sự, quản trị viên cần mở Nhân sự → Hồ sơ nhân viên và liên kết tài khoản; quyền kiểm duyệt không tự tạo hồ sơ lao động.",
    href: "/attendance",
    action: "Mở chấm công",
  },
];

const applicantTasks: GuideTask[] = [
  {
    id: "create",
    title: "Tạo và gửi hồ sơ đề cử",
    steps: [
      "Mở Hồ sơ của tôi và tạo hồ sơ mới; chọn đúng loại đề cử.",
      "Nhập thông tin chủ thể, tác phẩm và tải tài liệu chứng minh theo từng mục yêu cầu.",
      "Kiểm tra tên, quyền sử dụng nội dung và tài liệu đã tải, rồi gửi hồ sơ.",
    ],
    result: "Hồ sơ có mã tra cứu và trạng thái đã gửi trong Hồ sơ của tôi.",
    problem:
      "Nếu vẫn là Bản nháp, mở lại hồ sơ để xem trường còn thiếu trước khi gửi.",
    href: "/dossiers",
    action: "Mở hồ sơ của tôi",
  },
  {
    id: "follow",
    title: "Theo dõi và bổ sung hồ sơ",
    steps: [
      "Mở hồ sơ theo mã trong Hồ sơ của tôi hoặc từ Thông báo.",
      "Đọc trạng thái và yêu cầu bổ sung; cập nhật đúng tài liệu được nêu thay vì tạo hồ sơ mới.",
      "Kiểm tra phiên bản, gửi lại và theo dõi quyết định tiếp theo.",
    ],
    result: "Lần bổ sung được ghi nhận vào đúng hồ sơ và có trạng thái mới.",
    href: "/notifications",
    action: "Mở thông báo",
  },
  {
    id: "certificate",
    title: "Nhận và kiểm tra chứng thư",
    steps: [
      "Khi hồ sơ hoàn tất, mở Chứng thư và tìm theo mã hồ sơ.",
      "Đối chiếu tên tác phẩm, chủ sở hữu, phiên bản và trạng thái hiệu lực.",
      "Tải chứng thư nếu có; dùng mục Tra cứu chứng thư để kiểm tra mã với thông tin công khai.",
    ],
    result:
      "Chứng thư đúng hồ sơ và trạng thái tra cứu công khai khớp với hồ sơ cá nhân.",
    href: "/certificates",
    action: "Mở chứng thư",
  },
];

const viewerTasks: GuideTask[] = [
  {
    id: "search",
    title: "Tìm nội dung công khai",
    steps: [
      "Mở Tìm đề cử, nhập tên tác phẩm hoặc từ khóa, rồi thu hẹp bằng danh mục nếu cần.",
      "Mở kết quả để xem thông tin đã công bố; kiểm tra tên, chủ thể và trạng thái hiển thị.",
    ],
    result:
      "Bạn xem được nội dung công khai mà không cần quyền kiểm duyệt hay hồ sơ nhân viên.",
    href: "/search",
    action: "Tìm đề cử",
  },
  {
    id: "verify",
    title: "Tra cứu chứng thư",
    steps: [
      "Mở Tra cứu chứng thư và nhập mã chứng thư được cung cấp.",
      "Đối chiếu tên tác phẩm, chủ thể, thời điểm cấp và trạng thái hiện tại.",
      "Nếu chứng thư đã thu hồi hoặc không tìm thấy, kiểm tra lại mã và lịch sử phiên bản trước khi sử dụng thông tin.",
    ],
    result:
      "Bạn nhìn thấy tình trạng xác minh hiện tại và thông tin công khai của chứng thư.",
    href: "/verify",
    action: "Tra cứu chứng thư",
  },
];

function TaskSection({ task, index }: { task: GuideTask; index: number }) {
  return (
    <section
      className="scroll-mt-24 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-5 sm:p-7"
      id={task.id}
    >
      <p className="text-xs font-bold uppercase tracking-widest text-[var(--theme-accent)]">
        Việc {String(index + 1).padStart(2, "0")}
      </p>
      <h2 className="mt-2 text-xl font-bold text-[var(--theme-text)]">
        {task.title}
      </h2>
      <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-7 text-[var(--theme-text)] marker:font-bold marker:text-[var(--theme-accent)]">
        {task.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
      <p className="mt-5 rounded-lg bg-[var(--theme-elevated)] p-3 text-sm leading-6 text-[var(--theme-text)]">
        <strong>Kết quả cần thấy:</strong> {task.result}
      </p>
      {task.problem ? (
        <p className="mt-3 text-sm leading-6 text-[var(--theme-muted)]">
          <strong>Khi gặp vướng mắc:</strong> {task.problem}
        </p>
      ) : null}
      <Link
        className="mt-5 inline-flex min-h-11 items-center rounded-lg bg-primary-700 px-4 text-sm font-bold text-white hover:bg-primary-800"
        href={task.href}
      >
        {task.action}
      </Link>
    </section>
  );
}

export default function AccountGuidePage() {
  const user = useAuthUser();
  const persona = resolveWorkspacePersona(user?.roles ?? []);
  const isReviewer = persona === "MODERATOR";
  const isApplicant = persona === "USER";
  const tasks = isReviewer
    ? reviewerTasks
    : isApplicant
      ? applicantTasks
      : viewerTasks;
  const title = isReviewer
    ? "Hướng dẫn dành cho nhân viên kiểm duyệt"
    : isApplicant
      ? "Hướng dẫn tài khoản gửi hồ sơ"
      : "Hướng dẫn tài khoản tra cứu";
  const intro = isReviewer
    ? "Nhận quyền, xử lý hồ sơ được giao và sử dụng chấm công theo đúng thứ tự. Mỗi phần có kết quả để tự kiểm tra."
    : isApplicant
      ? "Tạo hồ sơ, theo dõi yêu cầu và kiểm tra chứng thư ngay trong tài khoản của bạn."
      : "Tìm nội dung và xác minh chứng thư công khai từ tài khoản tra cứu.";
  return (
    <main className="mx-auto max-w-5xl space-y-6 pb-12">
      <header className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-6 sm:p-8">
        <div className="flex items-center gap-2 text-sm font-semibold text-[var(--theme-accent)]">
          {isReviewer ? (
            <ClipboardCheck aria-hidden="true" className="size-5" />
          ) : isApplicant ? (
            <BookOpenCheck aria-hidden="true" className="size-5" />
          ) : (
            <Search aria-hidden="true" className="size-5" />
          )}
          Hướng dẫn trong tài khoản
        </div>
        <h1 className="mt-3 text-3xl font-bold text-[var(--theme-text)]">
          {title}
        </h1>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-[var(--theme-muted)]">
          {intro}
        </p>
      </header>
      <nav aria-label="Chọn việc cần làm" className="flex flex-wrap gap-2">
        {tasks.map((task) => (
          <a
            className="inline-flex min-h-11 items-center rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-4 text-sm font-semibold text-[var(--theme-text)] hover:bg-[var(--theme-elevated)]"
            href={`#${task.id}`}
            key={task.id}
          >
            {task.title}
          </a>
        ))}
      </nav>
      {tasks.map((task, index) => (
        <TaskSection index={index} key={task.id} task={task} />
      ))}
      <p className="flex items-start gap-2 text-sm leading-6 text-[var(--theme-muted)]">
        <ShieldCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        Hướng dẫn chung của nền tảng vẫn có tại{" "}
        <Link className="font-semibold underline" href="/guide">
          trang hướng dẫn công khai
        </Link>
        .
      </p>
    </main>
  );
}
