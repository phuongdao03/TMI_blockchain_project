import type { WorkspacePersona } from "@/lib/auth/role-workspaces";

export type PreviewScreen = {
  title: string;
  eyebrow: string;
  description: string;
  columns: readonly [string, string, string];
  rows: readonly (readonly [string, string, string])[];
};

const screens: Record<string, PreviewScreen> = {
  "/search": {
    title: "Tìm đề cử",
    eyebrow: "Tra cứu",
    description: "Tìm tác phẩm theo tên, lĩnh vực và trạng thái công bố.",
    columns: ["Tác phẩm", "Lĩnh vực", "Trạng thái"],
    rows: [
      ["Sắc màu di sản", "Văn hóa", "Đã công bố"],
      ["Hành trình nghề Việt", "Nghệ thuật", "Đang giới thiệu"],
    ],
  },
  "/works": {
    title: "Thư viện đề cử",
    eyebrow: "Khám phá",
    description: "Danh sách tác phẩm và tài liệu đã được giới thiệu công khai.",
    columns: ["Tác phẩm", "Danh mục", "Cập nhật"],
    rows: [
      ["Sắc màu di sản", "Tác phẩm", "24/09/2026"],
      ["Hành trình nghề Việt", "Tư liệu", "22/09/2026"],
    ],
  },
  "/verify": {
    title: "Tra cứu chứng thư",
    eyebrow: "Xác minh",
    description: "Kiểm tra thông tin chứng thư và trạng thái phát hành.",
    columns: ["Mã chứng thư", "Tác phẩm", "Trạng thái"],
    rows: [
      ["THV-2026-018", "Sắc màu di sản", "Có hiệu lực"],
      ["THV-2026-012", "Hành trình nghề Việt", "Có hiệu lực"],
    ],
  },
  "/notifications": {
    title: "Thông báo",
    eyebrow: "Cá nhân",
    description: "Theo dõi cập nhật liên quan đến hồ sơ và công việc.",
    columns: ["Nội dung", "Loại", "Thời gian"],
    rows: [
      ["Hồ sơ đã được tiếp nhận", "Hồ sơ", "Hôm nay"],
      ["Có cập nhật cần xem", "Hệ thống", "Hôm qua"],
    ],
  },
  "/account": {
    title: "Tài khoản",
    eyebrow: "Cá nhân",
    description: "Thông tin hiển thị và thiết lập tài khoản của bạn.",
    columns: ["Thông tin", "Giá trị minh họa", "Trạng thái"],
    rows: [
      ["Họ và tên", "Nguyễn Minh Anh", "Đang sử dụng"],
      ["Email", "minh.anh@example.com", "Đã xác minh"],
    ],
  },
  "/activity": {
    title: "Hoạt động gần đây",
    eyebrow: "Cá nhân",
    description: "Lịch sử thao tác được ghi nhận trên hệ thống.",
    columns: ["Hoạt động", "Đối tượng", "Thời gian"],
    rows: [
      ["Xem hồ sơ", "Sắc màu di sản", "Hôm nay"],
      ["Tra cứu chứng thư", "THV-2026-018", "Hôm qua"],
    ],
  },
  "/guide": {
    title: "Hướng dẫn",
    eyebrow: "Hỗ trợ",
    description: "Các bước sử dụng và câu hỏi thường gặp.",
    columns: ["Chủ đề", "Nội dung", "Cập nhật"],
    rows: [
      ["Tra cứu tác phẩm", "Tìm theo tên hoặc danh mục", "Mới nhất"],
      ["Theo dõi hồ sơ", "Xem tiến độ và phản hồi", "Mới nhất"],
    ],
  },
  "/dossiers": {
    title: "Hồ sơ của tôi",
    eyebrow: "Hồ sơ",
    description: "Theo dõi các hồ sơ đã tạo và tài liệu cần bổ sung.",
    columns: ["Hồ sơ", "Tài liệu", "Trạng thái"],
    rows: [
      ["Sắc màu di sản", "03 tài liệu", "Đang thẩm định"],
      ["Hành trình nghề Việt", "02 tài liệu", "Cần bổ sung"],
    ],
  },
  "/certificates": {
    title: "Chứng thư",
    eyebrow: "Hồ sơ",
    description: "Chứng thư đã phát hành cho các hồ sơ của bạn.",
    columns: ["Mã chứng thư", "Tác phẩm", "Phát hành"],
    rows: [
      ["THV-2026-018", "Sắc màu di sản", "18/09/2026"],
      ["THV-2026-012", "Hành trình nghề Việt", "11/09/2026"],
    ],
  },
  "/work-allocations": {
    title: "Công việc được giao",
    eyebrow: "Kiểm duyệt",
    description: "Hồ sơ và tài liệu được phân công thẩm định.",
    columns: ["Hồ sơ / tài liệu", "Vai trò", "Hạn xử lý"],
    rows: [
      ["Sắc màu di sản / Bản thuyết minh", "Thẩm định", "28/09/2026"],
      ["Sắc màu di sản / Hình ảnh", "Đối chiếu", "30/09/2026"],
    ],
  },
  "/attendance": {
    title: "Chấm công cá nhân",
    eyebrow: "Nhân sự",
    description: "Xem ca làm, trạng thái vị trí và lịch sử chấm công.",
    columns: ["Ngày", "Giờ vào", "Trạng thái"],
    rows: [
      ["24/09/2026", "08:03", "Đã ghi nhận"],
      ["23/09/2026", "07:58", "Đã ghi nhận"],
    ],
  },
  "/leave": {
    title: "Nghỉ phép",
    eyebrow: "Nhân sự",
    description: "Theo dõi số ngày phép và yêu cầu nghỉ của bạn.",
    columns: ["Khoảng thời gian", "Loại nghỉ", "Trạng thái"],
    rows: [
      ["02–03/10/2026", "Nghỉ phép năm", "Chờ duyệt"],
      ["15/09/2026", "Nghỉ phép năm", "Đã duyệt"],
    ],
  },
  "/overtime": {
    title: "Tăng ca",
    eyebrow: "Nhân sự",
    description: "Theo dõi yêu cầu tăng ca và số giờ đã duyệt.",
    columns: ["Ngày", "Số giờ", "Trạng thái"],
    rows: [
      ["25/09/2026", "02 giờ", "Chờ duyệt"],
      ["18/09/2026", "01,5 giờ", "Đã duyệt"],
    ],
  },
  "/admin/work-allocations": {
    title: "Phân công công việc",
    eyebrow: "Điều hành",
    description:
      "Phân chia công việc theo hồ sơ, tài liệu và nhân sự phụ trách.",
    columns: ["Hồ sơ / tài liệu", "Người phụ trách", "Tiến độ"],
    rows: [
      ["Sắc màu di sản / Bản thuyết minh", "Nguyễn Minh Anh", "Đang thực hiện"],
      ["Sắc màu di sản / Hình ảnh", "Trần Thu Hà", "Chờ tiếp nhận"],
    ],
  },
  "/admin/overtime": {
    title: "Duyệt tăng ca",
    eyebrow: "Nhân sự",
    description: "Xem và xử lý yêu cầu tăng ca của nhân viên.",
    columns: ["Nhân viên", "Thời gian", "Trạng thái"],
    rows: [
      ["Nguyễn Minh Anh", "25/09 · 2 giờ", "Chờ duyệt"],
      ["Trần Thu Hà", "23/09 · 1 giờ", "Đã duyệt"],
    ],
  },
  "/admin/leave": {
    title: "Duyệt nghỉ phép",
    eyebrow: "Nhân sự",
    description: "Theo dõi yêu cầu nghỉ và người đang chờ phê duyệt.",
    columns: ["Nhân viên", "Thời gian", "Trạng thái"],
    rows: [
      ["Nguyễn Minh Anh", "02–03/10/2026", "Chờ duyệt"],
      ["Trần Thu Hà", "27/09/2026", "Đã duyệt"],
    ],
  },
  "/admin/attendance": {
    title: "Chấm công toàn đội",
    eyebrow: "Nhân sự",
    description:
      "Theo dõi bản ghi chấm công, vị trí và các trường hợp cần xem xét.",
    columns: ["Nhân viên", "Giờ vào", "Trạng thái"],
    rows: [
      ["Nguyễn Minh Anh", "08:03 · 24/09", "Hợp lệ"],
      ["Trần Thu Hà", "08:17 · 24/09", "Chờ xem xét"],
    ],
  },
  "/admin/attendance/worksites": {
    title: "Điểm chấm công",
    eyebrow: "Cấu hình vị trí",
    description: "Quản lý địa điểm, vùng chấm công và lịch sử chính sách GPS.",
    columns: ["Địa điểm", "Múi giờ", "Bán kính"],
    rows: [
      ["Văn phòng TP. Hồ Chí Minh", "Asia/Ho_Chi_Minh", "250 m"],
      ["Văn phòng Hà Nội", "Asia/Ho_Chi_Minh", "300 m"],
    ],
  },
  "/admin/payroll": {
    title: "Bảng lương",
    eyebrow: "Tài chính nhân sự",
    description: "Theo dõi kỳ lương và các bước tính, kiểm tra, xác nhận.",
    columns: ["Kỳ lương", "Nhân viên", "Trạng thái"],
    rows: [
      ["Tháng 09/2026", "18 nhân viên", "Bản nháp"],
      ["Tháng 08/2026", "17 nhân viên", "Đã xác nhận"],
    ],
  },
  "/admin/employees": {
    title: "Nhân viên",
    eyebrow: "Nhân sự",
    description: "Danh sách nhân viên, phòng ban và trạng thái làm việc.",
    columns: ["Nhân viên", "Phòng ban", "Trạng thái"],
    rows: [
      ["Nguyễn Minh Anh", "Thẩm định", "Đang làm việc"],
      ["Trần Thu Hà", "Điều hành", "Đang làm việc"],
    ],
  },
  "/admin/departments": {
    title: "Phòng ban",
    eyebrow: "Nhân sự",
    description: "Cơ cấu phòng ban và người phụ trách.",
    columns: ["Phòng ban", "Trưởng bộ phận", "Nhân sự"],
    rows: [
      ["Thẩm định", "Nguyễn Minh Anh", "08 người"],
      ["Điều hành", "Trần Thu Hà", "05 người"],
    ],
  },
  "/admin/payments": {
    title: "Tài chính",
    eyebrow: "Điều hành",
    description: "Theo dõi yêu cầu thanh toán và chứng từ liên quan.",
    columns: ["Yêu cầu", "Số tiền", "Trạng thái"],
    rows: [
      ["Chi phí thẩm định", "2.400.000 đ", "Chờ xử lý"],
      ["Chi phí vận hành", "1.850.000 đ", "Đã duyệt"],
    ],
  },
  "/admin/dashboard": {
    title: "Tổng quan vận hành",
    eyebrow: "Điều hành",
    description: "Tình hình hồ sơ, nhân sự và công việc của hệ thống.",
    columns: ["Chỉ số", "Kỳ hiện tại", "Ghi chú"],
    rows: [
      ["Hồ sơ đang xử lý", "24", "03 cần ưu tiên"],
      ["Công việc đang thực hiện", "16", "07 nhân sự phụ trách"],
    ],
  },
  "/admin/users": {
    title: "Người dùng",
    eyebrow: "Quản trị",
    description: "Tài khoản người dùng và trạng thái truy cập.",
    columns: ["Tài khoản", "Vai trò", "Trạng thái"],
    rows: [
      ["minh.anh@example.com", "USER", "Hoạt động"],
      ["thu.ha@example.com", "VIEWER", "Hoạt động"],
    ],
  },
  "/admin/staff": {
    title: "Tài khoản nhân sự",
    eyebrow: "Quản trị",
    description: "Tài khoản nhân viên và vai trò trong hệ thống.",
    columns: ["Nhân viên", "Vai trò", "Trạng thái"],
    rows: [
      ["Nguyễn Minh Anh", "MODERATOR", "Hoạt động"],
      ["Trần Thu Hà", "SUPER_ADMIN", "Hoạt động"],
    ],
  },
  "/admin/content": {
    title: "Nội dung công bố",
    eyebrow: "Nội dung",
    description: "Tài liệu và bài viết đang chuẩn bị công bố.",
    columns: ["Nội dung", "Loại", "Trạng thái"],
    rows: [
      ["Giới thiệu chương trình", "Trang nội dung", "Đã công bố"],
      ["Tiêu chí đánh giá", "Tài liệu", "Bản nháp"],
    ],
  },
  "/admin/certificates": {
    title: "Quản lý chứng thư",
    eyebrow: "Chứng thư",
    description: "Theo dõi chứng thư và trạng thái phát hành.",
    columns: ["Mã chứng thư", "Tác phẩm", "Trạng thái"],
    rows: [
      ["THV-2026-018", "Sắc màu di sản", "Đã phát hành"],
      ["THV-2026-019", "Hành trình nghề Việt", "Chờ ký"],
    ],
  },
  "/admin/audit": {
    title: "Lịch sử hoạt động",
    eyebrow: "Kiểm soát",
    description: "Nhật ký thay đổi phục vụ đối chiếu và kiểm tra.",
    columns: ["Hoạt động", "Người thực hiện", "Thời gian"],
    rows: [
      ["Cập nhật phân công", "Trần Thu Hà", "24/09 · 09:12"],
      ["Duyệt nghỉ phép", "Trần Thu Hà", "23/09 · 16:24"],
    ],
  },
  "/admin/reports": {
    title: "Báo cáo",
    eyebrow: "Thống kê",
    description: "Tổng hợp dữ liệu hồ sơ, nhân sự và vận hành.",
    columns: ["Báo cáo", "Kỳ", "Trạng thái"],
    rows: [
      ["Tình hình thẩm định", "Tháng 09/2026", "Sẵn sàng"],
      ["Chấm công nhân sự", "Tháng 09/2026", "Đang cập nhật"],
    ],
  },
  "/admin/guide": {
    title: "Hướng dẫn quản trị",
    eyebrow: "Hỗ trợ",
    description: "Quy trình vận hành và hướng dẫn xử lý công việc.",
    columns: ["Chủ đề", "Nội dung", "Cập nhật"],
    rows: [
      ["Phân công công việc", "Chọn hồ sơ và tài liệu", "Mới nhất"],
      ["Kiểm tra chấm công", "Xem bằng chứng vị trí", "Mới nhất"],
    ],
  },
  "/blockchain": {
    title: "Ký blockchain",
    eyebrow: "Chứng thư",
    description: "Xem chứng thư chờ ký và lịch sử giao dịch.",
    columns: ["Chứng thư", "Tác phẩm", "Trạng thái"],
    rows: [
      ["THV-2026-019", "Hành trình nghề Việt", "Chờ ký"],
      ["THV-2026-018", "Sắc màu di sản", "Đã ghi nhận"],
    ],
  },
};

const common = ["/search", "/works", "/verify", "/notifications", "/account"];
const permittedPaths: Record<WorkspacePersona, readonly string[]> = {
  VIEWER: ["/dashboard", ...common, "/activity", "/guide"],
  USER: [
    "/dashboard",
    ...common,
    "/activity",
    "/guide",
    "/dossiers",
    "/certificates",
  ],
  MODERATOR: [
    "/work-allocations",
    ...common,
    "/guide",
    "/attendance",
    "/leave",
    "/overtime",
  ],
  SUPER_ADMIN: [
    "/admin",
    ...common,
    "/admin/guide",
    "/blockchain",
    ...Object.keys(screens).filter((path) => path.startsWith("/admin/")),
  ],
};

export function previewScreenFor(
  role: WorkspacePersona,
  path: string | undefined,
): PreviewScreen | null {
  if (!path || !permittedPaths[role].includes(path)) return null;
  return screens[path] ?? null;
}
