# Sửa lỗi nội dung hướng dẫn nạp tiền tái xuất hiện

Ngày: 05/11/2026.

## Nguyên nhân

- Câu giải thích định dạng số đã bị đưa lại vào `guide-fallback-content.ts`, trái với ví dụ bắt buộc trong yêu cầu UX writing.
- Tài liệu QA và đối chiếu trước/sau còn ghi sai rằng nên giữ câu này. Bộ kiểm thử trước đó không kiểm tra yêu cầu nội dung đó.

## Đã sửa

- Bước nhập tiền chỉ còn: “Nhập số tiền muốn nạp, tối thiểu 5.000đ.”
- `prepareGuideArticleBody` biên tập hai biến thể câu cũ đã xác định khi đọc nội dung CMS. Cả `/guide/[slug]` và `/help/[slug]` dùng chung hàm này; không ghi đè dữ liệu CMS.
- Giữ nguyên mức nạp, thời hạn 10 phút, nội dung chuyển khoản và hướng dẫn tránh thanh toán trùng. Chức năng chèn dấu phân cách trong ô nhập tiền không đổi.
- Bỏ ghi chú nội bộ “audit/rate/compensation” trong mô tả tăng ca và công việc; viết gọn thông báo khi chức năng rút chưa mở.
- Sửa tài liệu QA, đối chiếu trước/sau và nguyên tắc biên tập để không khuyến nghị đưa lại câu thừa.

## Xác minh

- Ba trường hợp hồi quy mới đã thất bại trước bản sửa: nguồn hướng dẫn mặc định và hai biến thể nội dung CMS cũ.
- Bổ sung hai trường hợp đọc bài từ CMS theo phạm vi công khai/tài khoản.
- 10 tệp kiểm thử liên quan: 32 kiểm thử đạt. ESLint các tệp sửa và TypeScript đạt.
- Tải lại `/guide/huong-dan-nap-tien-vao-vi` từ nguồn tại 390×844 và tải lại bình thường tại 1440×900: câu thừa không xuất hiện, bước nhập tiền đúng, không tràn ngang.
- Các điều kiện 5.000đ, 10 phút và lời nhắc không thanh toán trùng vẫn có trong giao diện. Đã mở lại tab bài viết đã sửa.
- Nội dung CMS cũ được mô phỏng trong kiểm thử; không sửa dữ liệu production và không chạy giao dịch thật.
