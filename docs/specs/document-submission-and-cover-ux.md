# Đặc tả: gửi tài liệu và ảnh bìa mobile-first

Trạng thái: người dùng đã duyệt phạm vi và kế hoạch; đang triển khai theo lát cắt.

## Mục tiêu

Người dùng hiểu cần cung cấp gì, tài liệu nào đã tải thành công và khi nào hồ sơ thực sự được gửi. Admin chọn bìa cho mọi loại tác phẩm mà không sửa tệp gốc hoặc nội dung chứng thư đã cấp.

## Giả định cần duyệt

- Giữ ba bước hiện có: Thông tin → Tài liệu → Kiểm tra và gửi; không thay đổi nghiệp vụ thẩm định.
- Người dùng cung cấp tài liệu; admin quyết định bìa và nội dung được phép công bố.
- Chọn ảnh đã nộp chỉ hiển thị ảnh tác phẩm phù hợp và được phép dùng để công bố, không hiển thị giấy tờ định danh/bằng chứng riêng tư làm ứng viên bìa.
- Bìa riêng được tải một lần qua luồng media hiện có; lưu tham chiếu và vùng cắt, không tải lại tệp nguồn để tạo từng phiên bản crop.
- Cho phép migration bổ sung cấu hình trình bày nếu mô hình hiện tại không đủ. Không thêm dependency hoặc đổi CI nếu chưa được duyệt riêng.

## Trải nghiệm người gửi

1. **Thông tin:** tên tác phẩm, giới thiệu, danh mục và các trường theo danh mục; nhóm nội dung liên quan, đánh dấu bắt buộc, hướng dẫn bằng ví dụ. Giữ chức năng lưu bản nháp hiện có và chỉ thông báo đã lưu sau phản hồi thành công.
2. **Tài liệu:** chọn mục đích tài liệu bằng ngôn ngữ nghiệp vụ. Mỗi yêu cầu hiển thị mô tả ngắn, bắt buộc/tùy chọn và giới hạn thực tế từ schema. Điện thoại có nút Chọn tệp nổi bật; kéo/thả chỉ là tiện ích desktop.
3. **Kiểm tra và gửi:** tóm tắt thông tin, số tài liệu hợp lệ và mục còn thiếu; nút Sửa dẫn về đúng bước. Phân biệt rõ Tải tệp với Gửi hồ sơ; chỉ cho gửi khi tài liệu bắt buộc đã được xác nhận theo quy tắc hiện hành.

Danh sách tệp hiển thị tên, dung lượng, mục đích, tiến độ và trạng thái bằng tiếng Việt. Có thử lại/xóa phù hợp trạng thái; lỗi một tệp không làm mất các tệp đã thành công. Thông báo mất kết nối/kiểm tra an toàn không giả lập thành công. Không tự gửi hồ sơ sau tải tệp.

Mobile dùng một cột, nội dung chính trước hướng dẫn phụ, điều hướng bước gọn và vùng thao tác tối thiểu 44px. Nút cuối trang không che nội dung hoặc thanh điều hướng hiện có; tính safe-area. Không xây thêm hàng loạt ô trang trí.

## Trải nghiệm chọn bìa của admin

- Một mục Ảnh bìa tác phẩm với hai lựa chọn rõ ràng: **Chọn ảnh đã nộp** / **Tải ảnh bìa riêng**. Giữ lựa chọn khung video hiện có khi tác phẩm có video.
- Ảnh đủ lớn trên mobile, có dấu chọn và trạng thái chọn bằng chữ. Nút **Dùng ảnh này** xác nhận lựa chọn; chưa lưu phải có chỉ báo rõ ràng.
- Bản xem trước ngang 16:9, thống nhất với bìa thư viện. Chỉnh vùng cắt bằng vị trí/thu phóng, có điều khiển bàn phím và đặt lại; không kéo giãn ảnh. Lưu cấu hình trên bản công bố, không trên metadata chứng thư.
- Chọn bìa không tự công bố tài liệu hoặc hồ sơ. Nếu ảnh chưa có quyền dùng công khai, không dùng nó làm bìa; yêu cầu xác nhận/quyền phù hợp qua luồng hiện hành trước khi dùng.
- Nếu chưa có bìa, hiển thị mẫu theo loại tác phẩm/tài liệu với tên tác phẩm; không dùng khung trống, không coi mẫu là ảnh đã tải. Dùng cùng mẫu ở thư viện và preview.
- Không tự lấy trang PDF, giấy tờ hoặc tài liệu riêng tư làm ảnh. Trích trang PDF không thuộc phạm vi lần này.

## Cấu trúc và phong cách code

- Người gửi: `frontend/src/components/dossiers/` và `frontend/src/components/media/`.
- Admin: `frontend/src/components/admin/`; trình bày công khai: `frontend/src/components/public/`.
- Cấu hình/kiểm quyền: `backend/app/modules/public/`, API admin và migration nếu cần; tái sử dụng module media.
- Test cạnh component, backend tại `backend/app/tests/`, E2E tại `frontend/e2e/`.
- Giữ token màu đỏ/vàng, component và API hiện có. Tách component theo chức năng, không đổi kiến trúc ngoài phạm vi.

Ví dụ quy ước:

```tsx
<Button disabled={!canConfirm || saving} onClick={confirmCover}>
  {saving ? "Đang lưu ảnh bìa…" : "Dùng ảnh này"}
</Button>
```

## Kế hoạch theo lát cắt

1. Tái hiện luồng gửi hiện tại, viết test thao tác và trạng thái lỗi; thiết kế lại bước Tài liệu trước (uploader/workspace và test, tối đa 5 file/lát cắt).
2. Làm gọn Thông tin và Kiểm tra và gửi; kiểm tra chuyển bước, lưu nháp, bổ sung hồ sơ và chống gửi lặp (form/workspace/test, tối đa 5 file/lát cắt).
3. Chốt hợp đồng cấu hình bìa và quyền truy cập; thêm migration/API/test nếu cần. Kiểm tra rollback migration, ràng buộc vùng cắt và không sửa dữ liệu đã xác lập.
4. Bổ sung chọn ảnh đã nộp và upload bìa riêng; kiểm thử lọc ảnh riêng tư, lỗi tải lên và lưu lựa chọn. Tách từng đường đi thành lát cắt không quá 5 file.
5. Thêm chỉnh vùng cắt, mẫu bìa và tích hợp thư viện/preview; kiểm thử bàn phím, mobile và nhất quán hiển thị. Tách UI crop và trình bày công khai thành hai lát cắt.
6. Kiểm tra browser ở 320/390/430/768/1024/1440px, review diff và cập nhật `docs/handoffs/document-submission-and-cover-ux.md`.

## Kiểm thử và lệnh

Viết test lỗi/hành vi trước khi sửa. Vitest cho hàng đợi upload, bước hồ sơ, chọn bìa và crop; pytest cho quyền, tham chiếu media và metadata bất biến; Playwright cho gửi hồ sơ và chọn bìa trên desktop/mobile. Xem screenshot, console và network ở local; không dùng tài liệu thật để test công bố.

```powershell
npm.cmd --prefix frontend run dev
npm.cmd --prefix frontend run test -- src/components/media/file-uploader.test.tsx src/components/dossiers/dossier-workspace.test.tsx src/components/dossiers/dossier-create-form.test.tsx
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
python -m pytest backend/app/tests -q
npm.cmd run format:check
```

## Ranh giới và nghiệm thu

- Luôn: giữ thay đổi mobile trước đó, xác thực server, giới hạn MIME/dung lượng theo chính sách hiện có, giữ tệp gốc và dấu vân tay không đổi, chạy kiểm thử trước bàn giao.
- Cần duyệt: đặc tả/kế hoạch này, thay đổi schema để lưu crop/bìa; dependency mới, thay đổi quyền hoặc CI ngoài nội dung đã chốt.
- Không bao giờ: tự công bố bằng chứng riêng tư; sửa/xóa chứng thư đã cấp; sửa `.env`, đưa secrets hoặc tài liệu gốc vào commit; push/deploy khi chưa được yêu cầu.
- Không cuộn ngang ở 320px; tiêu đề dài/tên tệp dài không phá bố cục; dùng bàn phím được; lỗi upload có hướng khắc phục.
- Tệp được xác nhận thành công vẫn hiện sau refetch; trạng thái đang kiểm tra không bị ghi thành thất bại tùy tiện. Người dùng nhận xác nhận gửi hồ sơ rõ ràng.
- Bìa riêng không tạo bản sao tệp tác phẩm; crop nhất quán ở thư viện, trang tác phẩm và preview. Bìa không làm thay đổi nội dung chứng thư.

## Rủi ro

- Upload bìa riêng không được gắn nhầm vào bộ bằng chứng đã ký: dùng tham chiếu editorial và quyền admin.
- Chọn tệp không đồng nghĩa upload đã xong hoặc hồ sơ đã gửi: dùng trạng thái thực từ hệ thống, không dựa vào animation/timer.
- Crop lưu theo tọa độ chuẩn hóa và xác thực giới hạn; không sửa file nguồn, không tin cấu hình client.
- Ảnh bìa riêng có vòng đời cần quản lý: không xóa media còn được tham chiếu; cleanup phải được xác định theo chính sách hiện có, không tự xóa dữ liệu trong nhiệm vụ này.
