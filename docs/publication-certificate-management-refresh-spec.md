# Quản lý nội dung công bố và chứng thư

## Mục tiêu

Quản trị viên tìm được hồ sơ cần xử lý, biết nội dung nào thực sự công khai và
dọn các bản thử nghiệm mà không làm mất lịch sử chứng thư đã cấp.

## Quy tắc

- Tác phẩm thử nghiệm do quản trị viên xác định được **lưu trữ có lý do** qua
  luồng hiện có; màn hình không đoán bản thử nghiệm qua tiêu đề hay mã. Bản đã
  lưu trữ không xuất hiện trong danh mục công khai nhưng vẫn truy vết được.
- Chứng thư đã cấp không có nút xóa. Trạng thái công khai, tra cứu trực tiếp và
  thu hồi phải được phân biệt; chứng thư thu hồi vẫn có trang xác minh và lịch
  sử phiên bản.
- Thay đổi quyền hiển thị chứng thư không tự xuất bản tác phẩm.

## Tiêu chí hoàn thành

1. Danh sách tác phẩm mặc định hiển thị mọi trạng thái, chọn bản đầu tiên để
   tránh khung biên tập rỗng; tìm kiếm, lọc và phân trang hoạt động với tổng số
   bản ghi từ API.
2. Trạng thái và hành động chuyển trạng thái chỉ hiển thị khi hợp lệ; không cho
   chuyển trạng thái khi có nội dung chưa lưu.
3. Danh sách chứng thư có tìm kiếm, lọc trạng thái chứng thư và trạng thái công
   bố, phân trang; mỗi bản ghi cho biết khả năng xuất hiện công khai và đường
   xác minh.
4. Các hành động chính dễ nhận biết; hành động điều chỉnh và quyền hiển thị
   không chen lấn thông tin tra cứu.
5. Giao diện sáng/tối, màn hình hẹp, trạng thái tải/rỗng/lỗi và bộ kiểm thử hiện
   có vẫn hoạt động.

## Triển khai

1. Viết kiểm thử cho phân trang, chọn tác phẩm mặc định và chuyển trạng thái hợp
   lệ.
2. Cải thiện danh sách tác phẩm và trình biên tập bằng API hiện có.
3. Viết kiểm thử rồi cải thiện danh sách chứng thư bằng API hiện có.
4. Kiểm tra TypeScript, lint, build và thao tác trong trình duyệt.

## Lệnh kiểm tra

- `npm.cmd test` trong `frontend`
- `npm.cmd run typecheck` trong `frontend`
- `npm.cmd run lint` trong `frontend`
- `npm.cmd run build` trong `frontend`

## Giới hạn

Không xóa dữ liệu thật, thay đổi chứng thư đã ký, thêm phụ thuộc hoặc thay đổi
API trong lần thiết kế này.
