# Spec: Quản lý và công khai chứng thư kết hợp

## Mục tiêu

Cho phép quản trị viên quản lý tập trung các chứng thư đã cấp mà không phá vỡ
tính bất biến của bằng chứng. Chứng thư gắn với tác phẩm đã xuất bản công khai
được phép xuất hiện trong thư viện và tìm kiếm; chứng thư không công bố vẫn xác
minh được bằng số chứng thư, QR hoặc liên kết trực tiếp; chứng thư thu hồi không
còn được khám phá nhưng lịch sử xác minh vẫn tồn tại.

## Quy tắc nghiệp vụ

- `PUBLIC + PUBLISHED + certificate ACTIVE/EXPIRED`: tác phẩm và chứng thư được
  khám phá công khai.
- `UNLISTED/PRIVATE` hoặc chưa xuất bản: không xuất hiện trong thư viện/tìm
  kiếm; chứng thư đã cấp vẫn tra cứu trực tiếp được.
- `REVOKED`: không xuất hiện trong danh sách, tìm kiếm, nổi bật hoặc liên quan;
  trang xác minh trực tiếp hiển thị trạng thái thu hồi.
- Chứng thư đã cấp không có thao tác xóa vật lý.
- Điều chỉnh nội dung đã xác lập phải tạo yêu cầu phiên bản mới; phiên bản cũ
  được giữ trong lịch sử.
- Quyền hiển thị được quản lý tại nội dung công bố để tránh hai nguồn trạng thái
  xung đột.

## Giao diện quản trị

Trang `/admin/certificates` cung cấp danh sách toàn hệ thống, tìm kiếm theo số
chứng thư/mã hồ sơ/tên tác phẩm, lọc trạng thái và trạng thái công bố. Mỗi dòng
cho phép xem trang xác minh, mở nội dung công bố liên quan, xem lịch sử/cập nhật
phiên bản và bắt đầu quy trình thu hồi. Không hiển thị nút xóa đối với chứng thư
đã cấp.

## Hợp đồng API

- `GET /api/v1/admin/certificates`: phân trang; hỗ trợ `search`, `status`,
  `publicationStatus`, `page`, `pageSize`.
- Phản hồi bổ sung trạng thái và liên kết nội dung công bố nhưng không lộ dữ
  liệu hồ sơ riêng tư.
- Giữ nguyên các API xác minh, phiên bản và thu hồi hiện hành.

## Kiểm thử

- Backend: phân quyền, bộ lọc, phân trang và chứng thư thu hồi bị loại khỏi truy
  vấn khám phá.
- Frontend: trạng thái rỗng/lỗi/tải, bộ lọc, liên kết hành động và không có thao
  tác xóa.
- Hồi quy: tra cứu trực tiếp chứng thư thu hồi vẫn trả về trạng thái `REVOKED`.

## Lệnh xác minh

- `pytest backend/app/tests -q`
- `npm --prefix frontend test -- --run`
- `npm --prefix frontend run typecheck`
- `npm run format:check`

## Ranh giới

- Luôn giữ lịch sử và audit log; mặc định riêng tư khi chưa công bố.
- Không đổi URL QR/tra cứu hiện hành.
- Không hard-delete, sửa trực tiếp metadata đã ký hoặc tự động công bố hồ sơ.

## Tiêu chí hoàn thành

- Quản trị viên quản lý được chứng thư toàn hệ thống từ một màn hình.
- Chỉ tác phẩm công khai có chứng thư chưa thu hồi xuất hiện trong khám phá.
- Mọi chứng thư đã cấp, kể cả đã thu hồi, vẫn xác minh trực tiếp được.
- Giao diện hoạt động tốt từ 320 px và không cung cấp hành động xóa chứng thư đã
  cấp.
