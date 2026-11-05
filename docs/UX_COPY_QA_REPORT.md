# Báo cáo QA nội dung UX tiếng Việt

**Ngày:** 05/11/2026
**Phạm vi:** bản source cục bộ; không ghi dữ liệu CMS hoặc giao dịch production.

## Số liệu kiểm kê

- **100 tệp route** được lập bản đồ source; số này gồm trang xem trước và tiện ích, không có nghĩa cả 100 trang đã được mở trực quan.
- **4 route** được kiểm tra trên trình duyệt cục bộ: hướng dẫn nạp tiền, cài ứng dụng, cộng đồng và đăng nhập.
- **33 nhóm nội dung** được ghi vào kiểm kê chi tiết: **32 nhóm đã chỉnh sửa**, **1 nhóm đã xác minh source vốn dùng tiếng Việt** (quản trị tiếp thị liên kết; chỉ bài kiểm thử cũ được cập nhật).
- Hướng dẫn nạp chỉ nêu “Nhập số tiền muốn nạp, tối thiểu 5.000đ.”; bỏ lời giải thích về định dạng số mà người dùng có thể tự quan sát.
- **Không có tổng số chuỗi giao diện toàn website đáng tin cậy**: nội dung nằm trong JSX, dữ liệu tạo động, CMS và phản hồi API, chưa có kho chuỗi tập trung để đếm từng câu. Vì vậy không suy diễn số nội dung giữ nguyên trên toàn hệ thống.
- Mức nạp tối thiểu 5.000đ, thời hạn yêu cầu 10 phút, thông tin chuyển khoản, điều kiện rút, trạng thái giao dịch và quyền truy cập được giữ nguyên.

## Kiểm tra tự động

- **Sửa lỗi nội dung tái xuất hiện:** 10 tệp, 32 kiểm thử liên quan đạt; ESLint các tệp sửa và TypeScript đạt. Đã bổ sung kiểm tra cho nguồn mặc định, hai biến thể CMS cũ và hai phạm vi đọc bài. Xem [biên bản sửa lỗi](handoffs/ux-copy-topup-regression.md).
- **Lượt kiểm thử toàn bộ frontend trước lần sửa tái phát:** 246 tệp, 1.055 kiểm thử đạt. Lượt này chưa có kiểm tra ngăn câu giải thích định dạng số xuất hiện trở lại; không dùng kết quả đó để khẳng định nội dung đã đạt yêu cầu.
- **TypeScript:** `npx.cmd tsc --noEmit --incremental false` đạt.
- **ESLint:** các lượt kiểm tra tập trung trên tệp đã sửa đạt, không có lỗi. Một lượt lint rộng hơn ghi nhận 4 cảnh báo biến/nhập khẩu chưa dùng trong `membership-chat-access-admin.tsx`; không liên quan đến nội dung vừa đổi.
- **`git diff --check`:** đạt. Git chỉ hiện cảnh báo CRLF/LF ở một số tệp bẩn sẵn trong workspace.
- **Build production:** chưa chạy vì máy chủ xem trước Next.js đang dùng thư mục `.next`; build có thể làm gián đoạn phiên xem hiện tại. Cần chạy trong CI hoặc sau khi dừng máy chủ xem trước.
- Một kiểm thử thanh toán hồ sơ in cảnh báo TanStack Query rằng fixture trả về `undefined` cho truy vấn nghĩa vụ phí; các kiểm thử vẫn đạt. Cảnh báo này cần dọn riêng nếu muốn loại bỏ tiếng ồn trong log.

## Kiểm tra trình duyệt

- `/guide/huong-dan-nap-tien-vao-vi`: giao diện tiếng Việt (`lang=vi`), desktop 1441×825; sau cập nhật kiểm tra lại ở 501×825, không tràn ngang. Hướng dẫn nêu mức tối thiểu 5.000đ, thời hạn 10 phút và cách xử lý nếu đã chuyển tiền. Kết quả sửa câu bị tái xuất hiện được ghi riêng trong biên bản sửa lỗi bên dưới.
- `/install`: giao diện tiếng Việt (`lang=vi`), có nút “Cài ứng dụng”, hướng dẫn theo iOS/Android/máy tính và không tràn ngang ở 390×844 và 501×825.
- `/community`: giao diện tiếng Việt, giao diện tối, không tràn ngang ở 390×844 và 1440×900. API danh sách chuyên mục trả 401 trong môi trường cục bộ; API bài viết trả 200 với danh sách rỗng, nên trạng thái “Chưa có bài viết nào” được giữ nguyên.
- `/login?next=%2Fworkspace`: giao diện tiếng Việt (`lang=vi`), không tràn ngang tại kích thước trình duyệt cục bộ.
- Chưa kiểm thử đăng nhập thật, tài khoản nhân sự/quản trị, dữ liệu CMS production, gửi thanh toán, rút tiền hoặc gửi hồ sơ thật.

## Nội dung cần chủ sở hữu duyệt

- Không sửa điều khoản, chính sách, tuyên bố pháp lý, dữ liệu CMS, thông báo email/API hoặc quy tắc tiền/lương. Chủ sở hữu nghiệp vụ và pháp lý cần duyệt các nội dung thuộc phạm vi này trước khi phát hành.
- Các route chỉ dành cho vai trò quản trị/thẩm định cần kiểm tra trực tiếp bằng tài khoản kiểm thử để xác nhận nội dung động và quyền hiển thị.

## Tệp source và kiểm thử trong đợt nội dung này

- **Hướng dẫn, ví, thanh toán, cài ứng dụng:** `guide-fallback-content.ts`, `guide-center.tsx`, `guide-article-reader.tsx`, `wallet-workspace.tsx`, `wallet-withdrawal-workspace.tsx`, `payment-workspace.tsx`, `dossier-payment-action.tsx`, `pwa-install-button.tsx`, `frontend/src/app/(public)/install/page.tsx`, `shells.tsx`.
- **Tài khoản và điều hướng:** `login-form.tsx`, `register-form.tsx`, `google-oauth-button.tsx`, `dashboard-navigation.tsx`, `dashboard-context-header.tsx`, `navigation-breadcrumb.tsx`, `role-dashboard-overview.tsx`, `affiliate-workspace.tsx`, `affiliate-presentation.ts`.
- **Hồ sơ và cộng đồng:** `dossier-workspace.tsx`, `use-dossier-preparation.ts`, `preparation-recovery-notice.tsx`, `community-feed.tsx`.
- **Vận hành:** `attendance-workspace.tsx`, `attendance-location-picker.tsx`, `attendance-location-exception-panel.tsx`, `admin-attendance-location-evidence.tsx`, `admin-attendance-workspace.tsx`, `admin-leave-workspace.tsx`, `admin-overtime-workspace.tsx`, `payroll-workspace.tsx`, `payroll-period-detail.tsx`, `moderator-hr-dashboard-summary.tsx`, `review-lifecycle-panel.tsx`, `review-assistance-panel.tsx`, `review-assignment-queue.tsx`, `certificate-version-queue.tsx`, `content-report-workspace.tsx`, `operations-dashboard.tsx`, `admin-events-workspace.tsx`, `task-workspace.tsx`, `advertising-admin-workspace.tsx`, `frontend/src/lib/geolocation.ts`, trang `/reviews`.
- **Hồ sơ, tải tệp và hội viên:** `file-uploader.tsx`, `use-media-uploader.ts`, `admin-user-workspace.tsx`, `employee-workspace.tsx`, `hr-dashboard-summary.tsx`, `membership-benefit-center.tsx`, `membership-admin-workspace.tsx`, `work-allocation-workspace.tsx`, `my-work-allocation-list.tsx`, `review-assignment-list.tsx`, `review-workspace.tsx`, `blockchain-signing-workspace.tsx`.
- **Giao dịch và rút tiền:** `frontend/src/lib/api/client.ts`, `frontend/src/lib/wallet-presentation.ts`, `admin-withdrawals-workspace.tsx`.
- **Ưu đãi và quảng cáo:** `promotion-campaign-list.tsx`, `promotion-distribution.tsx`, `promotion-media-library.tsx`, `promotion-reports.tsx`, `promotion-preview.tsx`, `presentation-editor.tsx`, `campaign-builder.tsx`, `promotion-admin-workspace.tsx`, `campaign-policy-fields.tsx`, `advertising-booking-panel.tsx`, `advertising-campaign-list.tsx`, `advertising-admin-workspace.tsx`, `voucher-wallet.tsx`, `voucher-detail.tsx`, `voucher-card.tsx`, `login-voucher.tsx`, `checkout-voucher-selector.tsx`.
- **Hội viên, khoản thu và nhãn vai trò:** `membership-pricing-page.tsx`, `membership-chat-access-admin.tsx`, `payment-request-workspace.tsx`, `ui-preview/page.tsx`, `preview-tabs/page.tsx`, `role-ui-preview.tsx`, `coming-soon-feature.tsx`, `promotion-types.ts`.
- **Kiểm thử đã cập nhật:** đăng nhập/đăng ký, hướng dẫn, cài ứng dụng, ví, thanh toán, rút tiền, điều hướng, affiliate người dùng/quản trị, hồ sơ, khôi phục bản nháp, chấm công, thẩm định, tạo chiến dịch, đặt lịch quảng cáo, yêu cầu thanh toán, thanh toán hồ sơ và kỳ lương.

## Giới hạn

Đây là rà soát source theo các nhóm thuật ngữ kỹ thuật và luồng ưu tiên, kèm kiểm tra trực quan ba route đại diện. Không coi số nhóm nội dung trong kiểm kê là tổng số chuỗi trên toàn website. Nội dung từ CMS/API và các trạng thái cần quyền đăng nhập phải được kiểm tra trong môi trường staging với tài khoản phù hợp.
