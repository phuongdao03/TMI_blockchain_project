# Báo cáo điều hướng Tinh Hoa Việt — 31/10/2026

## 1. Cấu trúc trước khi sửa

Header công khai có bảy liên kết ngang. Thanh dưới có bốn liên kết và nút “Thêm”
mở lại drawer dài. Workspace cá nhân và thẩm định dùng cùng thanh công khai.
Sidebar quản trị phân nhóm nhưng chưa thu gọn nhóm được.

## 2. Vấn đề phát hiện

- Drawer công khai chưa khóa cuộn nền; thiếu đóng khi back/forward, query,
  anchor và phiên thay đổi.
- Persona ưu tiên có thể làm mất lối vào thẩm định/hồ sơ khi có nhiều role.
- Giới thiệu, văn bản thành lập và thư viện ảnh thiếu lối vào trong menu.
- Header chưa có tìm kiếm; tìm đề cử và tra cứu bằng xác lập chưa tách rõ.
- Link tới anchor trên trang stream có thể cuộn trước khi section xuất hiện.
- Chevron trên link thường tạo cảm giác có submenu.
- Bản nháp có autosave và session backup, nhưng khi storage bị chặn, quay lại
  bằng điều hướng nội bộ cần thêm phục hồi trong bộ nhớ.

## 3. Sitemap mới

```text
Công khai
├─ Khám phá: Trang chủ / Đề cử / Cộng đồng / Tra cứu bằng xác lập
├─ Về Tinh Hoa Việt: Giới thiệu / Văn bản / Thư viện ảnh / Mục tiêu
├─ Tham gia: Gửi hồ sơ theo quyền / Quy trình / Cộng đồng hội viên
├─ Hỗ trợ: Hướng dẫn / Liên hệ / Điều khoản / Quyền riêng tư / Cài ứng dụng
└─ Tài khoản: Đăng nhập-đăng ký hoặc các lối vào đã được cấp quyền
Workspace
├─ Cá nhân: Tổng quan / Hồ sơ / Dịch vụ / Tài khoản / Hỗ trợ
├─ Thẩm định: Việc thẩm định / Công việc / Nhân sự / Tài khoản
└─ Quản trị: Nhóm nghiệp vụ lọc theo quyền hiện hữu
```

## 4. Menu mobile

Header 64px cộng safe area; logo chính thức, nút tìm và nút menu 44px. Thanh
dưới có Trang chủ / Khám phá / Gửi hồ sơ / Cộng đồng / Cá nhân. Ẩn Gửi hồ sơ nếu
tài khoản thiếu USER hoặc release preview hạn chế route. Không còn nút Thêm. Cá
nhân của khách dẫn đăng nhập với đích `/workspace`.

Drawer có nhóm rõ ràng, nút đóng luôn tiếp cận được khi cuộn, khóa cuộn nền,
Escape, vòng focus và trả focus. Các anchor giữ nguyên tên đang có; footer bổ
sung `lien-he`. Không tạo route thư viện ảnh giả.

## 5. Menu desktop

Giữ các đích chính và dropdown Về Tinh Hoa Việt bằng native details, mở bằng
click/Enter, Tab qua liên kết, Escape và click bên ngoài để đóng. Tìm kiếm dùng
autocomplete hiện có và `/works?query=...`; không thêm API. Tra cứu bằng xác lập
vẫn là `/verify`. Theme, tài khoản và cài ứng dụng giữ lại.

## 6. Theo phiên đăng nhập

Khách có đăng nhập/đăng ký; tài khoản đã xác minh có thông tin cá nhân và các
lối vào phù hợp. Đích quay lại từ header giữ pathname/query. Đăng xuất giữ cơ
chế thu hồi phiên, đồng bộ session và xóa query cache hiện hữu. Overlay đóng khi
phiên hoặc quyền thay đổi. Không gọi API riêng để dựng menu.

## 7. Workspace người dùng

Giữ hồ sơ, bằng xác lập, voucher, ví, hội viên, quảng cáo và tài khoản theo đúng
điều kiện hiện có. Không xóa tab/chức năng affiliate trong workspace hội viên.
Dossier autosave, revision và xử lý conflict giữ nguyên.

Nếu storage bị chặn, bản sao trong bộ nhớ có owner riêng giữ dữ liệu qua
unmount/remount nội bộ; logout xóa bản sao theo cơ chế hiện hữu. Chỉ xác nhận
rời link khi nội dung chưa lưu và không có bản sao bền trên thiết bị;
beforeunload tiếp tục bảo vệ reload/đóng trang.

## 8. Thẩm định và quản trị

Thẩm định viên có thanh dưới Thẩm định / Công việc / Thông báo / Tài khoản. Các
nhóm nhân sự vẫn theo điều kiện nhân viên. Admin dùng sidebar/drawer riêng; nhóm
có nút thu gọn, aria-expanded/aria-controls, giữ trạng thái khi chuyển trang
trong shell và mở lại drawer. Nhóm chứa trang hiện hành luôn mở. Các tài khoản
nhiều role giữ thêm lối vào hồ sơ/thẩm định được cấp.

Server/API guard, danh sách permission và điều kiện customer không đổi.

## 9. Route được bảo toàn

[Kiểm kê 97 page entry points](NAVIGATION_ROUTE_AUDIT_2026.md) ghi URL,
component, ngữ cảnh, bằng chứng guard, layout, điểm vào và redirect. Không đổi,
thêm hoặc xóa page route. Kiểm kê source không thay thế nghiệm thu API bằng tài
khoản thật. Dynamic route cần ID thực từ danh sách tương ứng.

## 10. File chỉnh sửa trong đợt điều hướng

- `components/layout/shells.tsx`: tích hợp header, drawer, thanh dưới theo ngữ
  cảnh.
- `components/layout/dashboard-navigation.tsx`: đa vai trò, nhóm quản trị.
- `components/layout/navigation-config.ts`: nhóm công khai và matcher dùng
  chung.
- `components/layout/navigation.css`: hình học, safe area, vùng chạm và theme.
- `components/layout/navigation-search.tsx`: overlay tìm kiếm tái sử dụng
  autocomplete.
- `components/layout/use-navigation-overlay.ts`: lifecycle, focus, cuộn và đóng
  overlay.
- `components/layout/use-navigation-anchor.ts`: chờ anchor của trang stream.
- `components/layout/navigation-breadcrumb.tsx`: breadcrumb ngắn cho trang con.
- `components/search/search-autocomplete.tsx`: focus và nút xóa tùy chọn.
- `components/dossiers/use-dossier-preparation.ts`: cảnh báo rời trang khi chưa
  có bản lưu.
- `components/dossiers/preparation-recovery-storage.ts`: phục hồi nội bộ khi
  storage bị chặn.
- `components/reviews/verdict-review-form.tsx`: thanh gửi dùng inset chung, nằm
  trên bottom navigation trên mobile.
- Các unit test tương ứng; `e2e/navigation-redesign.spec.ts`,
  `e2e/public-shell-layout.spec.ts`, `e2e/public-session-foundation.spec.ts`.
- Tài liệu audit/spec/report và handoff. Các thay đổi homepage/UIUX trước đó
  được giữ nguyên, không coi là diff mới của riêng đợt điều hướng.

## 11. Kết quả kiểm thử

- Build production, typecheck, lint các file thay đổi và `git diff --check`:
  đạt.
- Toàn bộ frontend ở checkpoint: **1.033 test / 241 file đạt** với hai worker.
  Lượt chạy nhiều worker ban đầu có ba ca thẩm định lỗi thời gian/tương tác;
  chạy riêng chín ca và chạy lại toàn bộ với hai worker đều đạt.
- Sau tinh chỉnh cuối, **63 ca liên quan** được xác nhận lại theo các file:
  shell 28, navigation 20, recovery 11, matcher 2, autocomplete 2. Không lấy
  checkpoint cũ làm tuyên bố đã chạy lại toàn bộ suite sau mỗi thay đổi nhỏ.
- E2E hợp nhất kết quả cuối theo từng test/project: **24 đạt, 4 bỏ qua đúng điều
  kiện viewport, 0 lỗi còn lại**. Bao gồm menu, dropdown bàn phím,
  anchor/back/forward, search/clear/Enter, đăng nhập/đăng xuất/refresh-only,
  đồng bộ đăng xuất qua tab và workflow gửi kết quả thẩm định.
- Ma trận 320/360/375/390/414/430/768/1024/1440 × hai theme × khách/applicant/
  reviewer/admin: **72 cấu hình**. Kiểm tra tràn ngang, nhãn, vùng chạm và số
  mục active; thanh gửi thẩm định được kiểm tra không chồng bottom bar.
- Đa role và capability được kiểm bằng unit, không suy rộng thành đã thử browser
  fixture đa role. Không chạy giao dịch thật hoặc thay đổi quyền API.
- [Chứng cứ browser](NAVIGATION_BROWSER_EVIDENCE_2026.json) ghi từng ca và
  project. Các lỗi trung gian về anchor, nền portal và fixture chờ phiên đã được
  sửa và kiểm lại; không bỏ qua rule accessibility để cho test qua.
- **16 scan axe không có vi phạm**: tám scan tìm kiếm trong E2E, hai header
  desktop và sáu drawer ở cả hai theme.
  [Kết quả header/drawer](NAVIGATION_ACCESSIBILITY_2026.json). Keyboard/focus
  được kiểm thêm bằng thao tác Tab/Shift+Tab/Escape.

## 12. Giới hạn còn lại

Chrome emulation không thay thế iPhone/Android thật hoặc trình đọc màn hình.
Chưa có dữ liệu người dùng thật về tỷ lệ bấm/hoàn thành hồ sơ, hay RUM p75. Các
trang nghiệp vụ dùng fixture QA cục bộ; chưa xác nhận toàn bộ API staging. Hạn
chế no-JS của public auth Suspense layout đã ghi ở báo cáo homepage vẫn còn; đợt
này không thay kiến trúc phiên đăng nhập.

## 13. Screenshot trước/sau

Có **14 ảnh** trong `docs/screenshots/navigation-2026/`, chụp trạng thái hoàn
chỉnh sau animation. Hai ảnh trước là header của bộ chứng cứ homepage trước đó;
không có ảnh drawer trước riêng, không dựng lại ảnh giả.

| Giao diện             | Sáng                                                             | Tối                                                            |
| --------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------- |
| Header trước, mobile  | [Ảnh trước](screenshots/navigation-2026/before-header-390.png)   | —                                                              |
| Header trước, desktop | [Ảnh trước](screenshots/navigation-2026/before-header-1440.png)  | —                                                              |
| Mobile mới            | [Sáng](screenshots/navigation-2026/mobile-light.png)             | [Tối](screenshots/navigation-2026/mobile-dark.png)             |
| Desktop mới           | [Sáng](screenshots/navigation-2026/desktop-light.png)            | [Tối](screenshots/navigation-2026/desktop-dark.png)            |
| Drawer công khai      | [Sáng](screenshots/navigation-2026/guest-drawer-light.png)       | [Tối](screenshots/navigation-2026/guest-drawer-dark.png)       |
| Tìm kiếm              | [Sáng](screenshots/navigation-2026/search-light.png)             | [Tối](screenshots/navigation-2026/search-dark.png)             |
| Thẩm định             | [Sáng](screenshots/navigation-2026/reviewer-drawer-light.png)    | [Tối](screenshots/navigation-2026/reviewer-drawer-dark.png)    |
| Quản trị              | [Sáng](screenshots/navigation-2026/super-admin-drawer-light.png) | [Tối](screenshots/navigation-2026/super-admin-drawer-dark.png) |

## 14. Tối ưu tiếp theo

Nghiệm thu trên Safari iOS/Chrome Android thật với bàn phím mở, notch, landscape
và cỡ chữ hệ thống lớn. Đo khả năng tìm văn bản thành lập/thư viện ảnh, bắt đầu
và quay lại hồ sơ bằng người dùng thực; điều chỉnh thứ tự menu dựa trên kết quả.
Kiểm chứng API staging theo các capability đang triển khai.
