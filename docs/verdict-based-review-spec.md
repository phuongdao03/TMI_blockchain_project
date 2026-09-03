# Duyệt hồ sơ theo kết luận

Trạng thái: Đã duyệt phạm vi ngày 03/09/2026.

## Vấn đề

Thang điểm 5T tạo phổ điểm dài và phụ thuộc cách chấm của từng nhân sự. Một con
số tổng không giải thích rõ hồ sơ đạt, thiếu hay không đạt ở đâu. Hồ sơ còn chứa
nhiều loại tài liệu với định dạng khác nhau nên người duyệt cần nhận biết đúng
tài liệu trước khi kết luận.

## Mục tiêu

- Hồ sơ mới được đánh giá bằng kết luận có căn cứ, không dùng điểm số.
- Mỗi tiêu chí có một trong bốn kết luận: `MEETS`, `NEEDS_CLARIFICATION`,
  `DOES_NOT_MEET`, `NOT_APPLICABLE`.
- Mỗi tài liệu hiển thị tên, loại do người nộp chọn, định dạng tệp, dung lượng
  và trạng thái kiểm tra.
- Kết quả hồ sơ dùng ba trạng thái nghiệp vụ hiện có: `APPROVE`, `SUPPLEMENT`,
  `REJECT`.
- Dữ liệu và giao diện của phiếu chấm điểm cũ tiếp tục đọc được.

## Phạm vi dữ liệu

`reviewRubric.assessmentMethod` là trường có phiên bản:

- Không có trường này hoặc là `SCORED`: dùng luồng điểm số cũ.
- `VERDICT`: tiêu chí không cần `weight` hay `thresholds`; phiếu dùng
  `criterionVerdicts`.

Mỗi `criterionVerdicts[key]` gồm `outcome`, `rationale` và `evidenceMediaIds`.
Các cột điểm cũ được giữ nguyên và để `null` đối với phiếu `VERDICT`. Không sửa
hoặc chuyển đổi phiếu đã gửi.

## Quy tắc kết quả

- `APPROVE`: mọi tiêu chí áp dụng đều `MEETS`; không có cổng bắt buộc bị trượt.
- `SUPPLEMENT`: có ít nhất một tiêu chí `NEEDS_CLARIFICATION`; phải có nội dung
  hướng dẫn bổ sung.
- `REJECT`: có ít nhất một tiêu chí `DOES_NOT_MEET` hoặc cổng bắt buộc `FAIL`;
  phải nêu căn cứ.
- `NOT_APPLICABLE` không tự tạo kết quả; phải còn ít nhất một tiêu chí áp dụng.

Backend là nơi áp dụng các quy tắc này. Frontend chỉ hướng dẫn và phản ánh lỗi
trả về.

## Tương thích và triển khai

- API hiện tại giữ nguyên đường dẫn; chỉ bổ sung trường tùy chọn.
- Tạo phiên bản mới cho rubric mặc định; phiên bản hồ sơ cũ tiếp tục tham chiếu
  rubric cũ.
- Audit history, file storage, route, phân quyền và luồng blockchain không thay
  đổi.
- Không phát giao dịch, không deploy contract và không thay đổi role Mainnet.

## Tiêu chí hoàn tất

- Rubric `VERDICT` hợp lệ khi không có trọng số/ngưỡng điểm.
- Không thể gửi phiếu thiếu kết luận/căn cứ hoặc có kết quả trái quy tắc.
- Reviewer thấy rõ loại và định dạng của từng tài liệu.
- Hồ sơ cũ vẫn hiển thị phiếu điểm; hồ sơ mới không hiển thị tổng điểm.
- Test backend, frontend, lint và typecheck đạt.
