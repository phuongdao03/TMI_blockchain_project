# Giao hồ sơ thẩm định từ bảng phân công

## Mục tiêu

- Quản trị viên nhìn thấy hồ sơ vừa nộp và giao trực tiếp một tác phẩm cho kiểm duyệt viên.
- Hồ sơ `SUBMITTED` hoặc `PRECHECK` được chuyển sang `UNDER_REVIEW` trước khi tạo review assignment.
- Mặc định toàn bộ tài liệu thuộc phạm vi giao, và người được chọn phụ trách toàn bộ phạm vi. Có thể mở phần tùy chỉnh để thay đổi.
- Phân công chỉ báo thành công sau khi được kích hoạt. Nhân viên thấy hồ sơ với liên kết mở trang chấm điểm.
- Công việc chung có người phụ trách được kích hoạt ngay; bản nháp cũ có thể kích hoạt tại danh sách quản trị.
- Lỗi tổng quan vận hành hiển thị mã lỗi, mã yêu cầu và số hồ sơ chờ xử lý lấy từ API hàng đợi khi API chỉ số gặp sự cố.

## Kiểm chứng

- Kiểm thử phân công hồ sơ mới nộp, phân công lại hồ sơ đang thẩm định, công việc chung và danh sách của nhân viên.
- Chạy kiểm tra kiểu, lint và các kiểm thử liên quan.
