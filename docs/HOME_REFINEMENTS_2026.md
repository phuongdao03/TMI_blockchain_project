# Chỉnh sửa trang chủ theo phản hồi — 31/10/2026

- **Tài liệu:** nhúng trình đọc 53 trang ngay trong trang, tự tải khi cuộn đến.
  Giữ chuyển trang, mục lục, nhập số trang, zoom và toàn màn hình. Tải PDF chỉ
  là lựa chọn lưu/chia sẻ bên dưới trình đọc.
- **Ảnh mobile:** khung ảnh gọn, nút chuyển 44×44px; select lọc bộ ảnh chữ 16px;
  sáu thumbnail chia ba cột, hai hàng cao 126px. Giữ lightbox, vuốt, zoom, bàn
  phím và trả focus.
- **Cộng đồng:** hai khối cân bằng có ảnh thực tế, nội dung và CTA riêng; hai
  cột desktop, một cột trên điện thoại.
- **Menu:** bỏ About/Về Tinh Hoa Việt trên desktop và mobile. Drawer bỏ các mục
  Trang chủ, Khám phá, Cộng đồng, Gửi hồ sơ đã có ở thanh dưới; giữ tra cứu, quy
  trình, hội viên, hỗ trợ và tài khoản. Section ID/route vẫn giữ.
- **Hero:** bỏ hộp chữ Tổ chức Tinh Hoa Việt.

Phản hồi này thay thế menu About và trình đọc modal trong báo cáo trước. Không
thay đổi API, quyền hay quy trình hồ sơ.

## Kiểm chứng

48 unit test liên quan đạt, gồm xác nhận lại active header sau rút gọn menu.
Typecheck, lint file thay đổi và production build đạt. Ma trận Chrome
320/360/375/390/414/430/768/1024/1440 × hai theme không tràn ngang; trình đọc
hiện ảnh trang thật, chuyển trang ngay trong trang. 12 scan axe ở các phần
gallery/tài liệu/cộng đồng không báo vi phạm. Chưa nghiệm thu thiết bị thật.

Hợp nhất các ca E2E cuối: **7 đạt, 1 viewport skip, 0 lỗi còn lại**.
[Chứng cứ](HOME_REFINEMENTS_EVIDENCE_2026.json). Ca tương tác gallery cuối chờ
thumbnail hydrate và tắt ghi trace để tránh làm chậm dev runtime.

## Ảnh sau chỉnh sửa

| Phần      | Mobile                                                                                                                             | Desktop                                                                                                                              |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Bộ ảnh    | [Sáng](screenshots/home-refinements-2026/gallery-light-390.png), [Tối](screenshots/home-refinements-2026/gallery-dark-390.png)     | [Sáng](screenshots/home-refinements-2026/gallery-light-1440.png), [Tối](screenshots/home-refinements-2026/gallery-dark-1440.png)     |
| Tài liệu  | [Sáng](screenshots/home-refinements-2026/proposal-light-390.png), [Tối](screenshots/home-refinements-2026/proposal-dark-390.png)   | [Sáng](screenshots/home-refinements-2026/proposal-light-1440.png), [Tối](screenshots/home-refinements-2026/proposal-dark-1440.png)   |
| Cộng đồng | [Sáng](screenshots/home-refinements-2026/community-light-390.png), [Tối](screenshots/home-refinements-2026/community-dark-390.png) | [Sáng](screenshots/home-refinements-2026/community-light-1440.png), [Tối](screenshots/home-refinements-2026/community-dark-1440.png) |
