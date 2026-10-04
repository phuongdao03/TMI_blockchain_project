# Bằng xác lập Tinh Hoa Việt và trải nghiệm di động

## Phạm vi

- Dùng tên **Bằng xác lập** trong giao diện, PDF mới, hướng dẫn và thông báo. Giữ đường dẫn và API `certificate` để liên kết cũ hoạt động.
- Bằng mới có số `THV-YYYY-…`. THV Proof Registry hiện chỉ ghi hash của hồ sơ và phiên bản, không ghi số bằng hoặc hỗ trợ giao dịch thu hồi bằng. Việc tái cấp dùng lại bằng chứng `recordProof` đã xác nhận của đúng phiên bản hồ sơ, tạo bản ghi/PDF mã THV mới, rồi đánh dấu mã CNS/TMI cũ đã thu hồi trong hệ thống. Lịch sử và giao dịch blockchain bất biến được giữ nguyên.
- Thông tin tác giả công khai phải thống nhất với tác phẩm. Bằng mới đóng băng tên tác giả đã được duyệt trong metadata; bằng cũ tiếp tục phản ánh dữ liệu đã ký tại thời điểm phát hành.
- Giao diện ưu tiên điện thoại: biểu trưng trống đồng đúng tỷ lệ, video có ảnh bìa và phát khi người xem chọn, các bước gửi và theo dõi hồ sơ dễ thấy, nhân viên thấy tác vụ cần xử lý.
- Một bộ nhận diện Tinh Hoa Việt từ logo hiện có; không dùng lại hình nhận diện cũ không đồng nhất.

## Tiêu chí nghiệm thu

1. Mã THV mới tra cứu được; mã cũ vẫn tra cứu được và hiện trạng thái thu hồi. Cả hai tham chiếu cùng bằng chứng `recordProof` của hồ sơ; metadata của bằng mới được kiểm tra bằng hash riêng trong cơ sở dữ liệu.
2. Thao tác tái cấp có chế độ xem trước, có thể chạy lại an toàn, từ chối hồ sơ thiếu `recordProof` đã xác nhận, và chỉ thu hồi bản ghi cũ trong cùng giao dịch cơ sở dữ liệu với việc hoàn tất PDF mới.
3. Bằng web và PDF mới ghi cùng tên, số, tác giả và đơn vị “Đề cử Tinh Hoa Việt”; các trường không có dữ liệu không được giả lập là đã công bố.
4. Trên màn hình điện thoại, logo/trống đồng không méo, menu và hành động chính dễ bấm, video không tự tải toàn bộ trước khi phát.
5. Luồng người dùng có lối vào rõ ràng tới hồ sơ, bổ sung tài liệu, trạng thái và tải bằng; luồng nhân viên có lối vào tác vụ đang chờ.
6. Kiểm tra bằng test trọng tâm, lint/typecheck/build và duyệt các trang chính ở viewport điện thoại nếu có trình duyệt khả dụng.

## Trình tự

1. Kiểm tra bất biến dữ liệu, trạng thái tái cấp và nguồn tên tác giả.
2. Thêm test và sửa số, nhãn, dữ liệu tác giả, tái cấp an toàn.
3. Thiết kế lại bằng web/PDF và đồng bộ thuật ngữ trên các màn hình.
4. Sửa hình ảnh di sản, video và luồng hồ sơ/nhân viên.
5. Kiểm thử và ghi hướng dẫn vận hành tái cấp production; không chạy lệnh đổi dữ liệu production trong quá trình phát triển.

## Cách triển khai tái cấp sau khi phát hành mã nguồn

1. Sao lưu cơ sở dữ liệu và kiểm tra worker tạo PDF, Cloudinary, THV Proof Registry đang hoạt động. Chạy các lệnh từ thư mục gốc dự án trên VPS sau khi image mới đã được triển khai.
   Trước khi chạy `prepare --apply`, đối chiếu tên tác giả ở các tác phẩm đã công bố và tạm dừng sửa thông tin công khai trong lúc tái cấp: tên này được chốt vào metadata/PDF mới tại bước chuẩn bị.
2. Xem trước số lượng bằng cũ sẽ chuẩn bị:

   ```bash
   docker compose --env-file infrastructure/.env.production \
     -f infrastructure/compose.production.yaml exec backend \
     python -m app.scripts.reissue_thv_certificates prepare
   ```

3. Chuẩn bị mã THV và PDF đang chờ. Bước này giữ mã cũ còn hiệu lực:

   ```bash
   docker compose --env-file infrastructure/.env.production \
     -f infrastructure/compose.production.yaml exec backend \
     python -m app.scripts.reissue_thv_certificates prepare --apply
   ```

4. Xem trước, rồi đưa các PDF mới vào hàng đợi worker:

   ```bash
   docker compose --env-file infrastructure/.env.production \
     -f infrastructure/compose.production.yaml exec backend \
     python -m app.scripts.reissue_thv_certificates render
   docker compose --env-file infrastructure/.env.production \
     -f infrastructure/compose.production.yaml exec backend \
     python -m app.scripts.reissue_thv_certificates render --apply
   ```

5. Worker tạo PDF từ metadata THV và giao dịch `recordProof` đã xác nhận. Khi PDF lưu thành công, cùng một giao dịch cơ sở dữ liệu sẽ chuyển bằng cũ sang `REVOKED`, bằng THV sang `ACTIVE`, và cập nhật tác phẩm công khai. Lặp lại `render` để xử lý hồ sơ còn chờ nếu worker từng lỗi; kiểm tra mẫu bằng cũ, bằng mới, tên tác giả và tệp PDF.

Nếu bước `prepare --apply` từ chối một bằng vì thiếu `recordProof`, không sửa thủ công mã hoặc gán giao dịch cũ. Điều tra bằng chứng hồ sơ trước khi tái cấp. Việc thu hồi ở đây là trạng thái trong hệ thống; giao dịch `recordProof` trên Polygon không bị xóa hoặc thu hồi.

## Kiểm tra trước khi bàn giao

- Bộ test backend: 980 đạt, 2 bỏ qua. Các test trọng tâm về tái cấp, tra cứu mã cũ/mới, PDF và trạng thái thu hồi khi blockchain tạm ngừng cũng đạt sau chỉnh sửa cuối.
- Bộ test frontend: 543 đạt; các test video, bằng xác lập và tải PDF chạy lại đều đạt.
- Ruff, mypy (401 tệp), TypeScript, ESLint và Next.js production build (65 route) đạt.
- Đã xem giao diện trang chủ trên viewport điện thoại ở hai chế độ sáng/tối. Các hành trình E2E liên quan đến trang công khai, tra cứu, hồ sơ và dashboard đạt trên Chrome desktop/mobile (21 đạt, 5 bỏ qua theo viewport); chế độ preview đạt 1 test. Chưa kiểm thử nội dung động với dữ liệu production hoặc chạy lệnh tái cấp trên VPS.

## Giới hạn vận hành

- Bằng THV mới tham chiếu bằng chứng hồ sơ `recordProof` đã xác nhận. Hợp đồng hiện tại không ghi riêng mã bằng THV và không có hàm thu hồi bằng trên blockchain; trạng thái thu hồi được quản lý trong cơ sở dữ liệu và hiển thị khi tra cứu mã cũ.
- Nếu worker tạo PDF lỗi, mã CNS/TMI cũ vẫn còn hiệu lực; chạy lại `render` sau khi xử lý lỗi. Không coi số THV ở trạng thái chờ là bằng đã phát hành.
