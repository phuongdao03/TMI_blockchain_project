# Kiểm toán nội dung UX toàn website

**Trạng thái:** Rà soát các nhóm nội dung trọng yếu trên bản đồ route; giới hạn runtime được ghi ở cuối tài liệu
**Ngày bắt đầu:** 05/11/2026
**Phạm vi:** Nội dung giao diện tiếng Việt trong website Tinh Hoa Việt

## Mục tiêu và tiêu chí hoàn tất

Viết nội dung ngắn gọn, tự nhiên, đúng trạng thái nghiệp vụ và giúp người dùng biết việc cần làm tiếp theo. Không thay đổi API, mã trạng thái, kiểm tra dữ liệu, phí, thời hạn, quyền hạn, luồng thanh toán hoặc quyền lợi hội viên.

- Rà soát trang công khai, xác thực, tài khoản, hồ sơ, thanh toán, ví, tiếp thị liên kết, cộng đồng, hội viên, quảng cáo, thẩm định và khu vực quản trị.
- Ghi nhận từng nội dung cần sửa theo màn hình, tệp, mức ưu tiên, câu hiện tại, đề xuất và trạng thái.
- Chỉ sửa bản dịch giao diện trong source. Không ghi đè nội dung CMS đang chạy, dữ liệu người dùng, văn bản pháp lý hoặc nội dung bên thứ ba.
- Kiểm tra lại các luồng và trạng thái liên quan bằng lint, kiểm tra kiểu, kiểm thử hiện có và trình duyệt khi môi trường cho phép.

## Cấu trúc dự án và cách kiểm tra

- `frontend/src/app`: route Next.js và bố cục trang.
- `frontend/src/components`: màn hình và thành phần giao diện.
- `frontend/src/lib`: nhãn trạng thái, định dạng và nội dung dùng chung.
- `backend/app`: thông báo API và kiểm tra đầu vào; chỉ sửa nội dung hiển thị, không đổi hợp đồng hoặc nghiệp vụ.
- Mốc quét ban đầu: 100 tệp route, 467 tệp component và 78 tệp thư viện. Số route bao gồm route xem trước và tiện ích nội bộ; đây không phải số trang người dùng đã kiểm tra trực quan.

Lệnh kiểm tra có sẵn trong `frontend/package.json`:

- `npm run lint`
- `npm run typecheck`
- `npm test -- <đường-dẫn-bài-kiểm-thử-liên-quan>`
- `npm run build`

## Ranh giới

**Được làm:** sửa câu chữ trong giao diện, nội dung trợ giúp tĩnh, nhãn và thông báo; rút gọn giải thích kỹ thuật không cần thiết; bổ sung chỉ dẫn an toàn khi đã có căn cứ nghiệp vụ.

**Không làm:** thay đổi dữ liệu giao dịch, trạng thái, validation, API, quyền truy cập, phí, hạn mức, thời hạn, tỷ lệ hoa hồng, nội dung pháp lý, dữ liệu người dùng hoặc nội dung CMS production.

Nếu phát hiện trạng thái UI có thể gây hiểu lầm nhưng cần đổi logic để sửa, ghi nhận riêng và không âm thầm đổi hành vi.

## Kế hoạch theo lát

1. **Lập kiểm kê:** quét route và nguồn nội dung; phân loại Public, User, Reviewer và Admin; ghi câu cần sửa trước khi chạm source.
2. **Ưu tiên P0:** hướng dẫn nạp, thanh toán, rút tiền, hồ sơ và trạng thái; giữ nguyên số tiền, thời hạn, điều kiện và cảnh báo cần thiết.
3. **Sửa P1:** đăng nhập, thông báo lỗi, thẩm định, chấm công, vận hành và các câu lộ chi tiết kỹ thuật.
4. **Sửa P2/P3:** cộng đồng, tiếp thị liên kết, biểu mẫu, trạng thái rỗng, điều hướng và tính nhất quán thuật ngữ.
5. **Rà soát trình duyệt và bàn giao:** kiểm tra mobile/desktop, giao diện sáng/tối, trạng thái lỗi và hoàn tất các tài liệu yêu cầu.

### Mốc rà soát

- [x] Chụp bản đồ route và nguồn nội dung ban đầu.
- [x] Sửa và kiểm tra các trường hợp P0 đã xác minh.
- [x] Sửa các trường hợp P1/P2 có thể xác nhận trực tiếp từ source.
- [x] Rà soát các route công khai và màn hình đại diện theo vai trò trong môi trường cục bộ.
- [x] Hoàn tất kiểm kê các trường hợp chọn lọc, bảng trước/sau và báo cáo QA.

## Kiểm kê nội dung cần cải thiện

| Ưu tiên | Route / màn hình | Tệp | Nội dung hiện tại | Vấn đề và nội dung đề xuất | Trạng thái |
|---|---|---|---|---|---|
| P0 | Hướng dẫn nạp tiền | `frontend/src/components/guide/guide-fallback-content.ts`, `guide-content.ts` | “Tạo lệnh nạp”; giải thích dấu chấm phân cách hàng nghìn | Dùng “Nạp tiền vào ví”; chỉ nêu mức tối thiểu 5.000đ và thao tác cần thiết. Loại câu giải thích định dạng khỏi nguồn mặc định và hai biến thể nội dung CMS cũ khi hiển thị. Giữ hạn 10 phút, đúng số tiền/nội dung chuyển khoản và cách xử lý khi tiền đã trừ; bổ sung kiểm tra hồi quy cho nguồn và cả hai phạm vi đọc bài. | Đã sửa |
| P0 | Ví · yêu cầu nạp hết hạn | `frontend/src/components/wallet/wallet-workspace.tsx` | Hướng dẫn tạo yêu cầu mới ngay sau khi yêu cầu cũ hết hạn | Tạo yêu cầu mới nếu chưa chuyển tiền; nếu đã chuyển thì không trả lần nữa, kiểm tra trạng thái và liên hệ hỗ trợ bằng mã yêu cầu. | Đã sửa |
| P0 | Thanh toán hồ sơ | `frontend/src/components/payments/payment-workspace.tsx` | Mô tả chu kỳ kiểm tra 3 giây, 5 phút và đối soát nền | Nêu trạng thái đang chờ xác nhận và khuyên kiểm tra giao dịch trước khi trả lại. | Đã sửa |
| P1 | Rút hoa hồng | `frontend/src/components/wallet/wallet-withdrawal-workspace.tsx` | Chi tiết xác nhận số dư từ máy chủ | Bỏ nội bộ triển khai; giữ hạn mức, điều kiện và bước kiểm tra trạng thái yêu cầu. | Đã sửa |
| P1 | Trạng thái rút tiền cần kiểm tra | `frontend/src/lib/wallet-presentation.ts`, `frontend/src/components/admin/admin-withdrawals-workspace.tsx` | “Chờ đối soát” | Dùng “Cần kiểm tra giao dịch” để người rút và nhân viên hiểu bước còn thiếu. | Đã sửa |
| P1 | Đăng nhập và đăng ký | `frontend/src/components/auth/login-form.tsx`, `register-form.tsx` | Thông tin cấu hình và lỗi liên kết tài khoản; cách gọi “username” | Dùng “tên đăng nhập”, mô tả mục đích đăng nhập và chỉ dẫn liên hệ hỗ trợ phù hợp. | Đã sửa |
| P1 | Tiếp thị liên kết | `frontend/src/components/affiliate/affiliate-workspace.tsx`, `frontend/src/lib/affiliate-presentation.ts`, `frontend/src/components/layout/dashboard-navigation.tsx` | Trạng thái chờ/tạm giữ và tên mục chưa thống nhất | Chuẩn hóa “Tiếp thị liên kết”, “Chờ duyệt”, “Đang tạm giữ”; thay nhãn dịch vụ bằng tiếng Việt. | Đã sửa |
| P1 | Chấm công cá nhân | `frontend/src/components/hr/attendance-workspace.tsx` | Thời gian máy chủ, trạng thái “Super Admin”, cách giải thích vị trí theo góc nhìn hệ thống | Nêu kết quả chấm công, việc chờ duyệt, yêu cầu vị trí và phạm vi ghi nhận bằng tiếng Việt dễ hiểu. Giữ điều kiện lịch làm/chính sách. | Đã sửa |
| P1 | Thẩm định và quản trị | `frontend/src/components/admin/review-lifecycle-panel.tsx`, `frontend/src/components/reviews/review-assistance-panel.tsx`, `frontend/src/app/(dashboard)/reviews/page.tsx` | “Admin”, “Reviewer”, “Moderator” trong nội dung hiển thị | Dùng “quản trị viên”, “người thẩm định”, “người kiểm duyệt”; không đổi phân quyền. | Đã sửa |
| P1 | Phát hành chương trình ưu đãi | `frontend/src/components/promotions/promotion-campaign-list.tsx`, `campaign-builder.tsx`, `promotion-admin-workspace.tsx` | “Backend”, “cutoff” và mô tả kỹ thuật | Nêu điều kiện xuất bản, thời hạn và ngân sách bằng tiếng Việt. | Đã sửa |
| P1 | Phát voucher | `frontend/src/components/promotions/promotion-distribution.tsx` | Nhắc đến backend trong bảo đảm chống cấp trùng | Diễn đạt kiểm tra lại danh sách người nhận khi phát và khi thử lại. | Đã sửa |
| P2 | Thư viện ảnh ưu đãi | `frontend/src/components/promotions/promotion-media-library.tsx` | “metadata trên máy chủ” | Bỏ chi tiết triển khai; giữ định dạng ảnh và giới hạn 5 MB. | Đã sửa |
| P2 | Đặt lịch quảng cáo | `frontend/src/components/advertising/advertising-booking-panel.tsx`, `advertising-campaign-list.tsx` | “ví nội bộ”, mô tả trừ tiền từ góc nhìn hệ thống | Nêu khoản thanh toán được trừ từ ví để xác nhận lịch. | Đã sửa |
| P2 | Cộng đồng · khách chưa đăng nhập | `frontend/src/components/community/community-feed.tsx` | “chế độ chỉ đọc”; mô tả chung về kết nối | Nêu rõ có thể xem nội dung công khai; cần đăng nhập để viết bài, bình luận hoặc theo dõi. | Đã sửa |
| P2 | Hồ sơ đã gửi | `frontend/src/components/dossiers/dossier-workspace.tsx`, `frontend/src/components/guide/guide-fallback-content.ts` | “chế độ chỉ đọc” | Nêu người dùng xem được hồ sơ/lịch sử và chỉ chỉnh sửa khi có yêu cầu bổ sung. | Đã sửa |
| P2 | Lưu phần chuẩn bị hồ sơ | `frontend/src/components/dossiers/use-dossier-preparation.ts`, `preparation-recovery-notice.tsx` | “đồng bộ” và bản khôi phục tạm theo góc nhìn trình duyệt | Nêu nội dung nào đã lưu, phần nào chưa lưu và việc cần làm tiếp theo. | Đã sửa |
| P2 | Tải thư viện hướng dẫn | `frontend/src/components/guide/guide-center.tsx` | “đang đồng bộ” | Dùng “đang tải” và nêu hướng dẫn thiết yếu vẫn dùng được khi thư viện chưa tải. | Đã sửa |
| P2 | Ví và hội viên | `frontend/src/components/wallet/wallet-workspace.tsx`, `membership-pricing-page.tsx` | “số dư trả trước nội bộ”, “ví nội bộ” | Nêu số dư trong ví dùng để thanh toán dịch vụ, không đổi cách dùng ví hoặc điều kiện gói. | Đã sửa |
| P2 | Nhãn tiền trong màn hình quản trị | `frontend/src/components/advertising/advertising-admin-workspace.tsx`, `frontend/src/components/promotions/campaign-policy-fields.tsx`, `frontend/src/components/admin/payment-request-workspace.tsx`, `frontend/src/components/payments/dossier-payment-action.tsx`, `frontend/src/components/hr/payroll-period-detail.tsx` | “(VND)” và “Đơn vị VND” | Dùng “đồng” trong nhãn hiển thị; giữ nguyên mã tiền tệ trong dữ liệu và API. | Đã sửa |
| P2 | Quản trị tiếp thị liên kết | `frontend/src/components/admin/admin-affiliate-workspace.tsx` | Ảnh tham chiếu có nhãn tiếng Anh; source hiện có tiêu đề/nút tiếng Việt nhưng bài kiểm thử còn dùng tiếng Anh | Giữ source đã Việt hóa; cập nhật kỳ vọng kiểm thử theo nhãn hiện tại. | Đã xác minh |
| P1 | Lỗi yêu cầu hết thời gian chờ | `frontend/src/lib/api/client.ts` | “Máy chủ phản hồi chậm. Vui lòng thử tải lại.” | Không khẳng định yêu cầu thất bại; nhắc kiểm tra trạng thái trước khi gửi lại để tránh thao tác trùng. | Đã sửa |
| P1 | Thao tác chi trả trong quản trị | `frontend/src/components/admin/admin-withdrawals-workspace.tsx` | “Xếp hàng payout thật”; “đối soát” | Dùng “Gửi lệnh chi trả”; nêu rõ kiểm tra trạng thái trước khi thử lại. | Đã sửa |
| P1 | Danh sách hồ sơ được giao | `frontend/src/components/reviews/review-assignment-list.tsx`, `review-workspace.tsx`, `frontend/src/components/work-allocations/my-work-allocation-list.tsx`, `work-allocation-workspace.tsx`, `frontend/src/components/admin/review-lifecycle-panel.tsx` | “hàng đợi” và “nhận việc trong hàng đợi” | Gọi là danh sách hồ sơ/công việc được giao; nêu bước xử lý tiếp theo. | Đã sửa |
| P1 | Tổng quan nhân sự | `frontend/src/components/hr/hr-dashboard-summary.tsx` | “hàng đợi nhân sự”, “kết nối lại với dịch vụ nhân sự” | Nêu danh sách yêu cầu, trạng thái tải và thao tác thử lại bằng ngôn ngữ trực tiếp. | Đã sửa |
| P2 | Tải tệp | `frontend/src/components/media/file-uploader.tsx`, `use-media-uploader.ts` | “xử lý hàng đợi tải tệp”, giữ tệp trong hàng đợi | Nêu tệp đang tải/kiểm tra và vị trí tệp còn được giữ. | Đã sửa |
| P2 | Yêu cầu quyền lợi hội viên | `frontend/src/components/membership/membership-benefit-center.tsx`, `membership-admin-workspace.tsx` | Nhắc hàng đợi quản trị và kiểm tra ở máy chủ | Nêu yêu cầu được xét theo chu kỳ hội viên, cách theo dõi và bước kiểm tra của bộ phận quản trị. | Đã sửa |
| P1 | Quản lý tài khoản và hồ sơ nhân sự | `frontend/src/components/admin/admin-user-workspace.tsx`, `hr/employee-workspace.tsx` | “kiểm tra quyền ở máy chủ”, “audit log”, “đồng bộ email” | Mô tả kết quả kiểm tra quyền, lịch sử thao tác và ràng buộc liên kết tài khoản. | Đã sửa |
| P1 | Giao dịch xác lập trên chuỗi khối | `frontend/src/components/blockchain/blockchain-signing-workspace.tsx` | “Đang tải hàng đợi”, “Hệ thống đối soát kết quả” | Gọi đúng nội dung là giao dịch chờ ký và giải thích trạng thái được xác nhận. | Đã sửa |
| P1 | Bằng chứng vị trí chấm công | `frontend/src/components/hr/attendance-location-exception-panel.tsx` | “Dữ liệu máy chủ nhận lúc” | Hiển thị “Thời điểm ghi nhận” và giữ mốc giờ UTC. | Đã sửa |
| P1 | Danh sách thẩm định và trạng thái vận hành | `frontend/src/components/admin/certificate-version-queue.tsx`, `review-assignment-queue.tsx`, `review-lifecycle-panel.tsx`, `content-report-workspace.tsx`, `operations-dashboard.tsx`, `frontend/src/components/reviews/review-workspace.tsx`, `review-assistance-panel.tsx`, `frontend/src/components/dashboard/role-dashboard-overview.tsx`, `frontend/src/components/advertising/advertising-admin-workspace.tsx`, `frontend/src/components/public/public-work-detail.tsx`, `frontend/src/components/notifications/notification-presentation.ts` | “hàng đợi”, vai trò “moderator” và một số mã trạng thái hiển thị trực tiếp | Gọi rõ loại danh sách, dịch vai trò và trình bày trạng thái bằng tiếng Việt; giữ nguyên mã trạng thái trong dữ liệu. | Đã sửa |
| P2 | Thuật ngữ ưu đãi và điều hướng | `frontend/src/components/vouchers/`, `frontend/src/components/promotions/`, `frontend/src/components/layout/shells.tsx`, `dashboard-navigation.tsx`, `dashboard-context-header.tsx`, `navigation-breadcrumb.tsx`, `frontend/src/components/admin/content-report-workspace.tsx`, `frontend/src/components/events/admin-events-workspace.tsx`, `frontend/src/components/guide/guide-fallback-content.ts` | “Voucher”, “Marketing”, “Trust & Safety”, “Menu”, “Website”, tên loại sự kiện tiếng Anh | Dùng “ưu đãi”, “tiếp thị”, “an toàn nội dung”, “điều hướng”, “trang web” và tên loại sự kiện bằng tiếng Việt. | Đã sửa |
| P1 | Hướng dẫn cài ứng dụng và quyền vị trí | `frontend/src/app/(public)/install/page.tsx`, `frontend/src/components/pwa/pwa-install-button.tsx`, `frontend/src/components/hr/attendance-workspace.tsx`, `frontend/src/lib/geolocation.ts`, `frontend/src/components/public/coming-soon-feature.tsx` | “website”, “menu trình duyệt” và chỉ dẫn thao tác rời rạc | Dùng “trang web”, “tùy chọn trình duyệt” và hướng dẫn bật quyền vị trí qua kết nối an toàn; giữ tên trình duyệt và giao thức HTTPS. | Đã sửa |
| P2 | Lịch sử thao tác trong chấm công và xử lý yêu cầu | `frontend/src/components/hr/admin-attendance-workspace.tsx`, `admin-overtime-workspace.tsx`, `admin-leave-workspace.tsx`, `frontend/src/components/hr/employee-workspace.tsx`, `frontend/src/components/tasks/task-workspace.tsx` | “audit log”, “audit”, “rate”, “compensation” trong xác nhận và mô tả nội bộ | Dùng “lịch sử thao tác”, “ghi lại” hoặc mô tả công việc cần làm; bỏ ghi chú triển khai khỏi mô tả tăng ca và công việc. Không đổi dữ liệu được lưu hay quy tắc tính tiền. | Đã sửa |

### Nội dung cần xác minh riêng

- Tại `/community`, máy chủ cục bộ không trả được danh sách chuyên mục. Chưa đủ dữ liệu để xác định trạng thái rỗng của bài viết có đúng hay không; không đổi logic truy vấn.
- Các route có quyền, dữ liệu thật hoặc yêu cầu đăng nhập nhân sự không thể được kiểm tra đầy đủ trên production. Cần rà theo từng vai trò sau khi có môi trường và tài khoản kiểm thử phù hợp.
- Nội dung do CMS, email, thông báo backend và bên thứ ba cung cấp không được sửa. Văn bản pháp lý, chính sách tiền/lương và tuyên bố tuân thủ cần chủ sở hữu nội dung duyệt trước khi phát hành.
- Số lượng route/component/thư viện là số tệp source tìm được; không đại diện cho số màn hình đã duyệt trực quan hoặc tổng số chuỗi hiển thị. Báo cáo QA ghi riêng số luồng đã mở và nhóm nội dung đã đánh giá để tránh suy diễn.
