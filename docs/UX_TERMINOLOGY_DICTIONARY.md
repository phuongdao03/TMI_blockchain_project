# Từ điển thuật ngữ giao diện Tinh Hoa Việt

| Khái niệm | Cách dùng thống nhất | Tránh trong nội dung người dùng | Ghi chú |
|---|---|---|---|
| Ví dịch vụ | Ví của tôi / ví | Ví nội bộ, ví trả trước nội bộ | Dùng “ví của tôi” cho điều hướng; “ví” trong câu ngắn. |
| Nạp tiền | Nạp tiền | Tạo lệnh nạp, khởi tạo lệnh nạp | Gọi kết quả là “yêu cầu nạp tiền” khi cần phân biệt một lần nạp cụ thể. |
| Yêu cầu nạp tiền | Yêu cầu nạp tiền | Lệnh nạp | Có thể dùng “mã yêu cầu nạp” để tra cứu. |
| Chuyển khoản | Chuyển khoản | Thực hiện giao dịch chuyển tiền | Giữ nguyên số tiền và nội dung chuyển khoản được cấp. |
| Mã QR | Mã QR | QR code | Có thể dùng QR trong câu ngắn sau khi đã nói rõ mã QR. |
| Rút hoa hồng | Yêu cầu rút tiền | Lệnh rút | Dùng “yêu cầu” khi chưa chi trả; không gọi là đã rút thành công. |
| Hoa hồng có thể rút | Có thể rút | Hoa hồng khả dụng (trừ khu vực vận hành) | Phân biệt với khoản đang chờ duyệt hoặc tạm giữ. |
| Referral / affiliate | Tiếp thị liên kết | Affiliate | Dùng thống nhất ở điều hướng và tiêu đề người dùng. |
| Referral code | Mã giới thiệu | Referral code | Giữ mã thực tế nguyên dạng để sao chép. |
| Referral link | Liên kết giới thiệu | Link giới thiệu | Nút: “Sao chép liên kết”. |
| Commission | Hoa hồng | Commission | Dùng tên trạng thái cụ thể khi có dữ liệu. |
| Pending review | Chờ xét duyệt | Pending | Không ngụ ý đã được duyệt. |
| On hold | Đang tạm giữ | On hold | Chỉ dùng khi trạng thái nguồn là `ON_HOLD`. |
| Available | Có thể rút | Available | Chỉ phản ánh số dư đủ điều kiện rút. |
| Dossier | Hồ sơ đề cử / hồ sơ | Dossier | Dùng “hồ sơ đề cử” khi cần phân biệt hồ sơ nhân sự. |
| Submission | Gửi hồ sơ | Submit | Không gọi “đã duyệt” khi chỉ mới tiếp nhận. |
| Read-only state | Chưa thể chỉnh sửa / chỉ xem | Chế độ chỉ đọc | Giải thích điều gì người dùng vẫn làm được và khi nào có thể sửa. |
| Review | Thẩm định / xét duyệt | Review | “Thẩm định” cho chuyên môn; “xét duyệt” cho quyết định. |
| Reviewer | Người thẩm định | Reviewer | Dùng cho vai trò chuyên môn đánh giá hồ sơ. |
| Moderator | Người kiểm duyệt | Moderator | Dùng cho vai trò kiểm duyệt cộng đồng. |
| Admin | Quản trị viên | Admin | Vai trò có quyền quản trị thông thường. |
| Super Admin | Quản trị viên cấp cao | Super Admin | Dùng khi cần nói đúng vai trò được phân quyền. |
| Payment pending | Đang chờ xác nhận thanh toán | Pending payment | Nêu rõ chưa xác nhận; tránh báo thanh toán thành công. |
| Successful payment | Đã thanh toán | Payment succeeded | Chỉ dùng sau khi trạng thái xác nhận là thành công. |
| Server / backend | Không hiển thị với người dùng | Máy chủ, backend | Dùng hành động/kết quả thực tế thay cho nơi xử lý. |
| Sync | Đã lưu / đang lưu / chưa lưu | Đồng bộ | “Đồng bộ” chỉ dùng trong tài liệu kỹ thuật. |
| API / request ID | Mã yêu cầu (nếu cần tra cứu) | API, request ID | Không lộ mã kỹ thuật; dùng mã hỗ trợ hiển thị cho người dùng. |
| Voucher / coupon | Ưu đãi; mã ưu đãi khi cần nhập mã | Voucher, coupon | Giữ nguyên tên chương trình do CMS hoặc đơn vị có thẩm quyền cung cấp. |
| Queue | Danh sách hồ sơ / yêu cầu chờ xử lý | Hàng đợi (trong nội dung hướng đến người dùng) | Nêu rõ loại hồ sơ hoặc việc cần xử lý. |
| Blockchain | Chuỗi khối trong nội dung giải thích; bằng xác lập trong điều hướng | Blockchain | Không dùng thuật ngữ kỹ thuật nếu người dùng chỉ cần biết nơi xem hoặc ký bằng. |
| Marketing | Tiếp thị | Marketing | Dùng “tiếp thị & khuyến mại” cho khu vực quản trị chiến dịch. |
| Trust & Safety | An toàn nội dung | Trust & Safety | Dùng cho màn hình tiếp nhận phản ánh và kiểm duyệt nội dung. |
| SLA | Thời hạn xử lý | SLA | Nêu mốc thời gian cụ thể nếu nghiệp vụ đã công bố. |
| Website / menu | Trang web / điều hướng | Website, menu | Chỉ dùng tên riêng hoặc nhãn do thương hiệu quy định khi đã được xác nhận. |

## Quy ước

- Mã trạng thái và trường dữ liệu trong API giữ nguyên trong code; chỉ lớp trình bày dùng nhãn tiếng Việt.
- Các tên pháp lý, tổ chức, sản phẩm, tên ngân hàng và thương hiệu được giữ nguyên theo nguồn chính thức.
- Nếu nghiệp vụ chưa xác định trạng thái hoặc thuật ngữ, không tự suy đoán; ghi nhận để chủ sở hữu sản phẩm xác nhận.
