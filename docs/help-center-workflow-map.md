# Bản đồ quy trình cho Trung tâm hướng dẫn

Ngày rà soát: 18/10/2026. Đây là bản đồ từ mã nguồn hiện tại; chưa xác nhận các điều kiện cấu hình và quyền cấp trực tiếp trên môi trường vận hành.

## Vai trò và điểm giao việc

| Người thực hiện | Bắt đầu và điều kiện | Thao tác, kết quả và người xử lý tiếp | Kết thúc hoặc ngoại lệ | Nguồn |
|---|---|---|---|---|
| Khách | Chưa đăng nhập | Tra cứu tác phẩm, bằng xác lập; đăng ký rồi xác minh tài khoản | Chỉ thấy nội dung công khai | `frontend/src/app/(public)`, `backend/app/modules/auth` |
| Người tra cứu (`VIEWER`) | Tài khoản đăng ký thông thường | Dùng tài khoản, thông báo, hoạt động; chọn nâng cấp để gửi hồ sơ | Chưa có quyền tạo hồ sơ | `frontend/src/lib/auth/role-workspaces.ts`, `frontend/src/components/layout/dashboard-navigation.tsx` |
| Người nộp (`USER`) | Tài khoản loại người nộp | Chọn loại hồ sơ → nhập trường theo biểu mẫu hiện hành → tạo bản nháp → bổ sung minh chứng → gửi → theo dõi → bổ sung khi được yêu cầu → nhận quyết định → thanh toán khi có yêu cầu phí → theo dõi phát hành | Bản nháp có thể sửa; hồ sơ đã gửi chỉ mở sửa khi cần bổ sung; bị từ chối là kết quả riêng; yêu cầu phí chỉ sau phê duyệt | `frontend/src/components/dossiers/dossier-create-form.tsx`, `dossier-workspace.tsx`, `backend/app/modules/dossiers/models.py`, `backend/app/modules/payments/service.py` |
| Người thẩm định (`MODERATOR`) | Được giao đúng hồ sơ và phiên bản | Mở hàng đợi → đọc hồ sơ, minh chứng → khai phiếu 5 tiêu chí và phát hiện → lưu nháp tự động → chọn đề xuất → xác nhận gửi → quản trị viên nhận kết quả | Xung đột lợi ích, hủy phân công hoặc phiên bản hồ sơ đổi sẽ chặn xử lý; gửi xong không tự công bố | `frontend/src/components/reviews/five-t-scorecard.tsx`, `backend/app/modules/reviews/service.py` |
| Quản trị (`SUPER_ADMIN`) | Có quyền vào khu vực quản trị | Tiếp nhận hồ sơ → phân công thẩm định → kiểm tra kết quả → quyết định; sau phê duyệt có thể phát hành yêu cầu phí hoặc miễn phí; quản lý phát hành, nhân sự, nội dung và báo cáo theo từng trang | Các module có điều kiện riêng; phân công hồ sơ và đầu việc chung là hai luồng khác nhau | `frontend/src/components/work-allocations`, `backend/app/modules/reviews/service.py`, `backend/app/modules/payments/service.py` |
| Nhân viên liên kết (`EMPLOYEE`, thuộc tính tài khoản, không phải role) | Có hồ sơ nhân viên liên kết | Chấm công theo điểm và lịch; gửi đơn nghỉ/tăng ca → người quản lý duyệt → xem kết quả | Thiếu liên kết nhân viên hoặc điểm/lịch áp dụng thì không hoàn tất thao tác | `backend/app/modules/hr/service.py`, `frontend/src/components/hr` |

## Trạng thái cần giải thích trong bài người nộp

`DRAFT` → `SUBMITTED` → `PRECHECK` → `UNDER_REVIEW` → `COUNCIL_REVIEW` → `APPROVED` là đường đi xét duyệt khả dĩ, không bảo đảm mọi hồ sơ đi qua tất cả bước. `NEEDS_SUPPLEMENT` cho phép sửa và gửi lại. `REJECTED`, `CANCELLED`, `REVOKED` là nhánh khác. Sau phê duyệt, yêu cầu phí có thể đưa hồ sơ sang `PAYMENT_PENDING`; thanh toán được xác nhận hoặc miễn phí hợp lệ đưa tới `PAID`, rồi các bước chuẩn bị, phát hành và công bố: `ANCHOR_PENDING`, `ANCHORED`, `CERTIFICATE_ISSUED`, `PUBLISHED`. Mã trạng thái và nhãn: `backend/app/modules/dossiers/models.py`, `frontend/src/components/dossiers/dossier-status.tsx`. Không hướng dẫn nạp số dư vì giao diện hiện có thanh toán theo yêu cầu phí của hồ sơ, không có ví số dư cho người nộp.

## Ma trận chức năng – quy trình – bài hướng dẫn

| Chức năng | Quy trình | Bài hiện có / bài chuyên sâu |
|---|---|---|
| Tạo và gửi hồ sơ | Người nộp | `create-and-submit-a-dossier`, `applicant-process-overview`, `prepare-dossier`, `create-dossier-draft`, `submit-dossier` |
| Theo dõi và bổ sung | Người nộp | `track-and-update-a-dossier`, `dossier-status-and-supplement`, `dossier-faq` |
| Thanh toán theo hồ sơ | Người nộp, quản trị | `dossier-payment-guide`, `admin-payment-requests`, `admin-fee-decision-process` |
| Thẩm định và chấm điểm | Người thẩm định | `review-an-assigned-dossier`, `review-process-and-scorecard`, `review-exceptions-faq` |
| Phân công thẩm định/đầu việc và quyết định hồ sơ | Quản trị | `admin-review-assignments`, `admin-work-allocations`, `admin-allocation-process`, `admin-dossier-decision-process` |
| Điểm và lịch chấm công | Quản trị, nhân viên | `admin-worksite-attendance`, `admin-attendance-configuration`, `employee-attendance` |
| Ngoại lệ chấm công và người kiểm duyệt | Quản trị | `admin-attendance-corrections`, `admin-reviewer-invitations` |
| Nhân sự, đơn nghỉ, tăng ca, lương | Quản trị, nhân viên | `admin-employee-payroll`, `admin-employee-requests`, `employee-leave-request`, `employee-overtime-request` |
| Người dùng, nội dung, bằng, báo cáo, thông báo, cộng đồng, hướng dẫn | Quản trị | Các bài `admin-*` trong `0116_role_workflow_guides.py` |

## Giới hạn xác minh

- Loại hồ sơ, trường bắt buộc và minh chứng thay đổi theo phiên bản biểu mẫu; bài viết chỉ chỉ cách đọc biểu mẫu đang hiển thị, không khẳng định một danh mục cố định.
- Không tìm thấy chức năng nạp tiền vào số dư người nộp, quy trình hoàn tiền tự phục vụ hoặc chấm công bằng điểm số; không viết hướng dẫn cho các chức năng đó.
- Chưa xác minh giao diện production bằng tài khoản của từng vai trò. Quyền cấp trực tiếp có thể tạo khác biệt so với menu theo role.
- Các module quản trị khác đã có bài thao tác ban đầu, nhưng vẫn cần đối chiếu dữ liệu và cấu hình thật trước khi khẳng định mọi ngoại lệ vận hành.
