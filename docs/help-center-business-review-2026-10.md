# Báo cáo rà soát hướng dẫn nghiệp vụ

Ngày 18/10/2026. Bản đồ quy trình, quan hệ giữa vai trò và ma trận chức năng nằm tại [help-center-workflow-map.md](help-center-workflow-map.md). Phạm vi 4 vai trò và nhóm nhân viên liên kết nằm tại [help-center-role-coverage.md](help-center-role-coverage.md).

## Kết quả triển khai

- 4 vai trò sản phẩm: `VIEWER`, `USER`, `MODERATOR`, `SUPER_ADMIN`. `EMPLOYEE` là điều kiện tài khoản liên kết hồ sơ nhân viên, không phải vai trò thứ năm.
- Kho hướng dẫn có 46 bài sau migration mới. 15 bài mới gồm: `applicant-process-overview`, `prepare-dossier`, `create-dossier-draft`, `submit-dossier`, `dossier-status-and-supplement`, `dossier-payment-guide`, `dossier-faq`, `review-process-and-scorecard`, `review-exceptions-faq`, `admin-attendance-configuration`, `admin-attendance-corrections`, `admin-allocation-process`, `admin-dossier-decision-process`, `admin-fee-decision-process`, `admin-reviewer-invitations`.
- Viết lại bài `admin-user-accounts` để bỏ thao tác yêu cầu bổ sung hồ sơ không tồn tại trên trang Người dùng; hướng dẫn đúng thao tác tìm, lọc, đình chỉ và khôi phục. Migration chỉ sửa bản seed chưa được quản trị viên biên tập.
- FAQ mới tập trung vào lỗi gửi và sửa hồ sơ, trạng thái thanh toán, xung đột phân công, lưu nháp/chốt phiếu thẩm định, quyền đình chỉ tài khoản. FAQ được đặt trong bài theo giai đoạn để tìm ngay tại bước gặp lỗi.
- Nội dung mới liên kết giữa bài tổng quan và bài thao tác. Quyền xem bài theo vai trò vẫn được lọc bằng API hiện có; không thay đổi giao diện hoặc nghiệp vụ sản phẩm.

## Những điều đã đối chiếu

- Loại hồ sơ, trường bắt buộc và tài liệu là dữ liệu từ biểu mẫu hiện hành, không phải danh sách cố định: `dossier-create-form.tsx`, `dossier-workspace.tsx`.
- Trạng thái hồ sơ và quyền sửa/gửi lại: `dossiers/models.py`, `dossier-status.tsx`, `dossier-workspace.tsx`.
- Yêu cầu phí chỉ phát hành cho hồ sơ đã phê duyệt; người nộp trả theo yêu cầu phí hoặc hồ sơ được miễn phí: `payments/service.py`, `payment-request-workspace.tsx`, `dossier-payment-action.tsx`, `payment-workspace.tsx`.
- Phiếu 5 tiêu chí, điểm 0–20 mỗi tiêu chí, điều kiện gửi và đề xuất: `five-t-rubric.ts`, `five-t-scorecard.tsx`, `reviews/service.py`.
- Hai loại phân công, tiến độ từng người và thao tác hoàn thành: `generic-allocation-form.tsx`, `dossier-allocation-form.tsx`, `my-work-allocation-list.tsx`.
- Điểm chấm công, chính sách vùng và phân công: `attendance-configuration-workspace.tsx` cùng các trang chấm công nhân viên/quản trị.
- Quyết định cuối cần báo cáo phân công hoàn tất; thu phí hoặc miễn phí là hai lựa chọn sau phê duyệt: `review-lifecycle-panel.tsx`, `payment-request-workspace.tsx`.

## Chưa xác minh hoặc còn giới hạn

- Chưa đăng nhập bằng tài khoản production của từng vai trò. Bản xem trước dùng dữ liệu migration và tài khoản kiểm thử cục bộ; chưa chứng minh các cấu hình thật như loại hồ sơ, mức phí, điểm chấm công hay người được phân công.
- Các bài quản trị còn lại trong `0116_role_workflow_guides.py` đã có thao tác, nhưng chưa được mở rộng thành tài liệu chuyên sâu cho mọi ngoại lệ của nhân sự, bảng lương, công bố, bằng xác lập, thông báo, cộng đồng và báo cáo. Không đánh dấu các module này là đã hoàn chỉnh toàn bộ.
- Quyền cấp trực tiếp ngoài role có thể mở trang chức năng nhưng chưa có nhóm người đọc tương ứng trong CMS; cần kiểm tra tài khoản kiểu này trước khi coi ma trận quyền là tuyệt đối.
- Không có luồng nạp số dư cho người nộp, hoàn tiền tự phục vụ hoặc rút hồ sơ qua UI được xác nhận. Bài mới không hướng dẫn các thao tác ấy.

## Thay đổi và kiểm thử

- Thêm `backend/alembic/versions/0119_detailed_business_workflow_guides.py` và `0120_correct_admin_user_guide.py`; cập nhật `backend/app/tests/test_cms_guide_migration.py`, `docs/help-center-role-coverage.md` và tài liệu bản đồ này.
- Migration lên và xuống qua SQLite: 2 bài kiểm thử đạt; service/API hướng dẫn: 6 bài kiểm thử đạt. Ruff đạt cho cả hai migration mới.
- Bản xem trước cục bộ hiển thị đúng bài tổng quan người nộp, phiếu thẩm định cho người kiểm duyệt và cấu hình chấm công cho quản trị viên. Đây là kiểm tra giao diện với dữ liệu cục bộ, không phải kiểm thử môi trường production.
