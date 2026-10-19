# Phạm vi hướng dẫn theo vai trò

Ngày rà soát: 2026-10-18. Nguồn: `backend/app/modules/auth/roles.py`,
`backend/app/modules/cms/service.py`, menu tại
`frontend/src/components/layout/dashboard-navigation.tsx`, các trang và
thành phần nghiệp vụ được dẫn bên dưới. Đây là ma trận kiểm chứng bằng
source; chưa xác nhận với tài khoản production.

| Người đọc | Công việc | Hướng dẫn | Kiểm chứng |
|---|---|---|---|
| Khách | Tìm đề cử công khai | `explore-nominations` | `/works` |
| Khách | Đăng ký và đăng nhập | `create-account-and-sign-in` | `/register`, `/login` |
| Khách | Tra cứu bằng xác lập | `verify-a-certificate` | `/verify` |
| Khách | Câu hỏi dùng chung | `common-account-and-guide-questions` | Chỉ chứa nội dung công khai |
| Mọi tài khoản đã đăng nhập | Tên hiển thị, ảnh đại diện, thông tin liên hệ | `personal-profile-settings` | `/account`, thẻ Hồ sơ cá nhân |
| Người tra cứu (`VIEWER`) | Tra cứu và dùng tiện ích cá nhân | `viewer-account-basics` | Menu `/works`, `/verify`, `/notifications`, `/account`, `/activity` |
| Người gửi hồ sơ (`USER`) | Tạo và gửi hồ sơ | `create-and-submit-a-dossier` | `/dossiers` |
| Người gửi hồ sơ (`USER`) | Toàn bộ hành trình, chuẩn bị, tạo bản nháp, gửi | `applicant-process-overview`, `prepare-dossier`, `create-dossier-draft`, `submit-dossier` | `/dossiers/new`, `/dossiers/[id]` |
| Người gửi hồ sơ (`USER`) | Theo dõi và bổ sung | `track-and-update-a-dossier` | `/dossiers`, `/notifications` |
| Người gửi hồ sơ (`USER`) | Trạng thái, bổ sung, thanh toán và câu hỏi thường gặp | `dossier-status-and-supplement`, `dossier-payment-guide`, `dossier-faq` | `/dossiers/[id]`, `/payments/[orderId]` |
| Người gửi hồ sơ (`USER`) | Xem và cập nhật bằng | `my-certificates` | `/certificates` |
| Người kiểm duyệt (`MODERATOR`) | Thẩm định hồ sơ | `review-an-assigned-dossier` | `/reviews`, phiếu thẩm định |
| Người kiểm duyệt (`MODERATOR`) | Chấm phiếu, gửi kết quả và xử lý ngoại lệ | `review-process-and-scorecard`, `review-exceptions-faq` | `/reviews/[assignmentId]` |
| Người kiểm duyệt (`MODERATOR`) | Theo dõi đầu việc | `moderator-work-allocations` | `/work-allocations` |
| Nhân viên có hồ sơ liên kết (`EMPLOYEE`) | Chấm công | `employee-attendance` | `/attendance` |
| Nhân viên có hồ sơ liên kết (`EMPLOYEE`) | Gửi đơn nghỉ | `employee-leave-request` | `/leave` |
| Nhân viên có hồ sơ liên kết (`EMPLOYEE`) | Đăng ký tăng ca | `employee-overtime-request` | `/overtime` |
| Quản trị viên (`SUPER_ADMIN`) | Phân công và theo dõi thẩm định | `admin-review-assignments` | `/admin/reviews` |
| Quản trị viên | Quyết định cuối sau khi có báo cáo | `admin-dossier-decision-process` | `/admin/reviews/[dossierId]` |
| Quản trị viên | Giao đầu việc | `admin-work-allocations` | `/admin/work-allocations` |
| Quản trị viên | Tạo và theo dõi hai loại phân công | `admin-allocation-process` | `/admin/work-allocations` |
| Quản trị viên | Yêu cầu thanh toán | `admin-payment-requests` | `/admin/payments` |
| Quản trị viên | Thu phí hoặc miễn phí | `admin-fee-decision-process` | `/admin/payments` |
| Quản trị viên | Thiết lập điểm chấm công | `admin-worksite-attendance` | `/admin/attendance/worksites` |
| Quản trị viên | Thiết lập vùng, phân công và xem ngoại lệ chấm công | `admin-attendance-configuration` | `/admin/attendance/worksites`, `/admin/attendance` |
| Quản trị viên | Xét ngoại lệ và điều chỉnh bản ghi chấm công | `admin-attendance-corrections` | `/admin/attendance` |
| Quản trị viên | Mời và quản lý người kiểm duyệt | `admin-reviewer-invitations` | `/admin/staff` |
| Quản trị viên | Quản lý nhân viên và bảng lương | `admin-employee-payroll` | `/admin/employees`, `/admin/payroll` |
| Quản trị viên | Xử lý đơn nghỉ và tăng ca | `admin-employee-requests` | `/admin/leave`, `/admin/overtime` |
| Quản trị viên | Quản lý phòng ban | `admin-departments` | `/admin/departments` |
| Quản trị viên | Tra cứu tài khoản | `admin-user-accounts` | `/admin/users` |
| Quản trị viên | Công bố nội dung | `admin-publish-content` | `/admin/content` |
| Quản trị viên | Quản lý bằng xác lập | `admin-certificate-management` | `/admin/certificates` |
| Quản trị viên | Lịch sử và báo cáo | `admin-audit-reports` | `/admin/audit`, `/admin/reports` |
| Quản trị viên | Soạn và xuất bản hướng dẫn | `admin-guide-publishing` | `/admin/guide/articles` |
| Quản trị viên | Gửi thông báo | `admin-send-announcement` | `/admin/notifications` |
| Quản trị viên | Xử lý báo cáo cộng đồng | `admin-community-reports` | `/admin/community` |
| Quản trị viên | Ghi nhận hồ sơ đã duyệt | `admin-sign-record` | `/blockchain` |

Các bài dùng chung chỉ được gắn `PUBLIC`. Bài nghiệp vụ được gắn đúng một
vai trò hoặc `EMPLOYEE`. Quyền xem danh sách, tìm kiếm và trang chi tiết
được lọc ở máy chủ theo vai trò hiện tại và trạng thái liên kết nhân viên;
quản trị viên không còn tự nhận bài của các nhóm khác. Quyền biên tập bài
viết vẫn ở khu vực quản lý riêng.

Quyền được cấp trực tiếp cho tài khoản ngoài vai trò chưa được biểu diễn
thành nhóm người đọc của bài viết. Cần kiểm tra với tài khoản kiểm thử có
quyền tương ứng trước khi khẳng định trải nghiệm đầy đủ cho trường hợp đó.

Migration chỉ thay bài gốc chưa qua biên tập khi làm rõ ngôn ngữ công khai;
không ghi đè bài do quản trị viên sửa. Chưa có tài khoản production để đối
chiếu menu, tìm kiếm và trạng thái từng vai trò trực tiếp trên website.
