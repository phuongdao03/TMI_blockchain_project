# Quản lý địa điểm và nhân viên chấm công

## Cải tiến luồng chuyển văn phòng

- Đưa quản lý nhân viên lên trước cấu hình GPS; thu gọn GPS vào mục mở rộng. Biểu mẫu thêm chỉ mở khi quản trị viên chọn thêm hoặc sửa lịch.
- Khi chọn nhân viên, tải đủ các trang phân công ở mọi địa điểm (kể cả tạm ngưng). Hiển thị các giai đoạn trùng ngay cạnh ngày bắt đầu, trước khi gửi yêu cầu.
- Cho phép xác nhận chuyển một phân công đang mở sang địa điểm đang chọn: ngày kết thúc cũ = ngày bắt đầu mới trừ một ngày. Backend kiểm tra nhân viên, giai đoạn, lịch sử chấm công, chính sách GPS và các xung đột khác trước khi cập nhật; kết thúc cũ và tạo mới trong cùng transaction.
- Không tự chuyển nếu có nhiều xung đột hoặc ngày bắt đầu mới không sau ngày bắt đầu cũ; hiện từng phân công để chỉnh ngày kết thúc. Không xóa dữ liệu lịch sử.
- Thứ tự thực hiện: kiểm thử chuyển và từ chối lịch sử → API chuyển nguyên tử → giao diện xung đột và bố cục → kiểm thử frontend/backend và trình duyệt.
- Xác minh: `python -m pytest app/tests/test_global_attendance_admin.py`, `node node_modules/vitest/vitest.mjs run src/components/hr/attendance-configuration-workspace.test.tsx`, TypeScript và lint. Không đổi schema hoặc thêm dependency.

## Mục tiêu

Super Admin chọn một văn phòng và quản lý nhân viên được phân công tại đó mà không phải đoán từ danh sách toàn hệ thống. Địa điểm không còn sử dụng không làm rối danh sách mặc định.

## Hành vi

- Mặc định hiển thị địa điểm đang hoạt động. Có nút xem địa điểm tạm ngưng và kích hoạt lại. “Xóa khỏi danh sách” đặt địa điểm thành tạm ngưng; không xóa chính sách GPS, phân công hoặc lịch sử chấm công.
- Sau khi chọn văn phòng, hiển thị phân công nhân viên của chính văn phòng đó trước biểu mẫu thêm mới. Quản trị viên có thể tìm hồ sơ nhân viên đang hoạt động để thêm vào văn phòng.
- Mỗi phân công có thao tác “Sửa lịch” điền sẵn nhân viên và lịch vào biểu mẫu tạo giai đoạn kế tiếp; quản trị viên kết thúc giai đoạn cũ trước ngày bắt đầu giai đoạn mới. “Gỡ khỏi văn phòng” điều chỉnh ngày kết thúc có lý do; không xóa hồ sơ nhân viên.
- Các API chặn giai đoạn chồng nhau và chặn ngày kết thúc làm mất hiệu lực bản ghi chấm công. Chính sách GPS phải hiệu lực ở ngày bắt đầu phân công mới.

## Phạm vi kỹ thuật và kiểm tra

- Dùng API `PATCH attendance-worksites/{id}`, `GET/POST attendance-assignments` và `PATCH attendance-assignments/{id}` hiện có. Không cần migration hoặc quyền mới.
- Frontend: `attendance-configuration-worksite-panel`, `attendance-configuration-assignment-panel`, `attendance-configuration-workspace`. Kiểm tra bằng Vitest, TypeScript, ESLint và Prettier.
- Không xóa vật lý địa điểm, phân công hoặc hồ sơ nhân viên có lịch sử. Việc sửa lịch tạo giai đoạn mới để giữ cách tính chấm công cũ.
