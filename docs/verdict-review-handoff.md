# Bàn giao: thẩm định theo kết luận

## Kết quả

- Hồ sơ mới dùng kết luận theo từng tiêu chí thay cho điểm số 5T.
- Kết quả cuối được suy ra từ các kết luận, không cho nhân viên chọn tùy ý.
- Mỗi kết luận phải có nhận định và tài liệu dẫn chiếu; từng tệp cũng phải được kiểm tra.
- Trang reviewer hiển thị loại tài liệu, định dạng và dung lượng bằng nhãn dễ đọc.
- Hồ sơ và phiếu điểm cũ vẫn đọc được bằng giao diện tương thích.

## Quy tắc kết quả

- Có điều kiện bắt buộc không đạt hoặc tiêu chí `DOES_NOT_MEET`: `REJECT`.
- Có tiêu chí `NEEDS_CLARIFICATION`: `SUPPLEMENT`.
- Các tiêu chí còn lại đạt hoặc không áp dụng, đồng thời có ít nhất một tiêu chí áp dụng: `APPROVE`.
- `SUPPLEMENT` và `REJECT` bắt buộc có phản hồi gửi người nộp.

## Dữ liệu và migration

- Migration `0073_verdict_based_reviews` thêm `reviews.criterion_verdicts`.
- Migration tạo phiên bản cấu hình hồ sơ mới với `assessmentMethod=VERDICT`; không sửa hoặc xóa phiên bản cũ.
- Điểm cũ, nhận xét cũ, audit history, API route và dữ liệu hồ sơ được giữ nguyên.

## Kiểm thử

- Backend mục tiêu, migration và API: đã đạt.
- Toàn bộ backend: `740 passed, 2 skipped`.
- Toàn bộ frontend trước thay đổi E2E cuối: `323 passed`.
- Format, lint và typecheck toàn workspace đã đạt trước cập nhật E2E cuối.
- E2E reviewer đã được chuyển sang dữ liệu rubric `VERDICT`, gồm kiểm tra loại/định dạng tệp, kết luận tự động, gửi phiếu và dark mode.

## Việc còn lại trước production

- Chạy lại frontend unit test và E2E trên runner có quyền tạo file tạm trong `frontend/node_modules/.vite-temp`.
- Chạy migration thử trên bản sao database production và xác nhận version mới của từng loại hồ sơ.
- Không cần và không được gửi giao dịch blockchain cho thay đổi này.
