# Hướng dẫn viết nội dung giao diện tiếng Việt

## Giọng điệu

- Chuyên nghiệp, điềm tĩnh, lịch sự và gần gũi; xưng hô trực tiếp bằng “bạn”.
- Nói rõ điều gì đã xảy ra, trạng thái hiện tại và việc người dùng có thể làm tiếp theo.
- Dùng câu chủ động, động từ cụ thể: “Nạp tiền”, “Gửi hồ sơ”, “Kiểm tra trạng thái”, “Liên hệ hỗ trợ”.
- Tránh câu dài, lời quảng cáo chung chung, tiếng lóng và cách nói quan liêu.

## Viết cho người dùng

- Chỉ giải thích thông tin cần để hiểu, quyết định hoặc hoàn tất thao tác.
- Không mô tả cách phần mềm được lập trình: API, backend, máy chủ, đồng bộ, hàng đợi, chu kỳ làm mới, định dạng tự động.
- Không nhắc lại điều giao diện đã thể hiện rõ, như nút đổi màu khi chọn hoặc danh sách nằm bên dưới.
- Hướng dẫn nhập tiền dùng “Nhập số tiền muốn nạp, tối thiểu 5.000đ.” Không thêm câu giải thích dấu chấm phân cách hoặc việc định dạng tự động; chức năng định dạng vẫn hoạt động trong ô nhập.
- Nếu cần nói về lưu dữ liệu, dùng kết quả người dùng quan tâm: “Đã lưu”, “Một số thay đổi chưa được lưu”.
- Hướng dẫn nhiều bước chỉ giữ khi thao tác không hiển nhiên hoặc có rủi ro; sắp xếp theo trình tự người dùng thực hiện.

## Trạng thái và lỗi

- Phân biệt đã tạo yêu cầu, đang chờ xác nhận, đã thanh toán, bị từ chối và đã hoàn tất. Không báo thành công khi mới gửi yêu cầu.
- Với giao dịch chưa xác nhận, nói rõ tiền đã được ghi nhận hay chưa nếu có dữ liệu; nhắc kiểm tra lịch sử trước khi thanh toán lại.
- Với lỗi, nêu việc người dùng nên làm: kiểm tra kết nối, thử lại, giữ nguyên dữ liệu hoặc liên hệ hỗ trợ kèm mã hồ sơ/yêu cầu.
- Không hứa chắc về bảo mật, thời gian xử lý, hoàn tiền hay kết quả nếu chính sách và dữ liệu chưa xác nhận.
- Không yêu cầu người dùng gửi mật khẩu, mã xác minh hoặc giấy tờ nhạy cảm qua kênh không phù hợp.

## Tiền, ngày giờ và điều kiện

- Dùng cách viết quen thuộc tại Việt Nam: `5.000đ`, `1.250.000đ`; không thêm giới hạn hoặc phí ngoài cấu hình nghiệp vụ.
- Giữ nguyên số tiền, thời hạn, điều kiện, phí và trạng thái nguồn. Nếu nội dung nguồn chưa rõ, ghi để chủ sở hữu nghiệp vụ duyệt.
- Nói rõ đơn vị và thời điểm áp dụng khi thông tin đó ảnh hưởng quyết định của người dùng.
- Với yêu cầu có thời hạn, diễn đạt theo yêu cầu của người dùng, ví dụ “Yêu cầu có hiệu lực trong 10 phút”.

## Nhãn, trợ giúp và khả năng tiếp cận

- Tiêu đề mô tả mục tiêu hoặc kết quả; nút bắt đầu bằng động từ ngắn.
- Nhãn biểu mẫu đặt theo dữ liệu cần nhập; trợ giúp đặt sát trường liên quan.
- Trạng thái không chỉ dựa vào màu hoặc biểu tượng; nội dung vẫn phải đọc và hiểu được.
- Thông báo lỗi nên có thể đọc bằng công nghệ hỗ trợ, không biến cảnh báo thành văn bản trang trí.
- Dùng cùng một thuật ngữ ở điều hướng, tiêu đề, hướng dẫn, nút và lịch sử.

## Khu vực quản trị

- Có thể giữ mã nghiệp vụ, ghi chú nội bộ và thuật ngữ chuyên môn trong công cụ vận hành khi chúng cần thiết cho công việc.
- Nội dung hướng tới nhân viên vẫn phải viết bằng tiếng Việt dễ hiểu; gọi vai trò bằng tên tiếng Việt thống nhất.
- Không đưa chi tiết triển khai vào lời xác nhận dành cho quản trị viên nếu lợi ích vận hành có thể nói trực tiếp.

## Quy trình biên tập

1. Xác định người đọc, trạng thái nghiệp vụ và nguồn dữ liệu của câu.
2. Đánh dấu thông tin bắt buộc: tiền, phí, thời hạn, quyền, điều kiện và rủi ro.
3. Viết câu ngắn theo hành động hoặc kết quả; không thêm lời hứa mới.
4. So sánh bản trước/sau và xác nhận không đổi hành vi.
5. Chạy kiểm thử liên quan, lint/kiểm tra kiểu và xem giao diện ở trạng thái phù hợp.
6. Ghi rõ nội dung động, khu vực khóa quyền hoặc môi trường chưa thể xác minh.
