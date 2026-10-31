# Trang chủ Tinh Hoa Việt — mobile first

## Audit và phạm vi

Đọc README, DESIGN, cấu hình Next/React/Tailwind, public layout/header/footer,
`app/(public)/page.tsx`, `institution-content`, `heritage-gallery`,
`mission-content`, `deferred-proposal-viewer`, `proposal-viewer`,
`home-account-experience`, `featured-assets`, `welcome-music` và test liên quan.

- Giữ: logo/ảnh thật, 38 ảnh và danh mục hiện có, PDF quyết định gốc, proposal
  và 53 trang ảnh thật, nhạc chủ động bật, API đề cử công bố, auth/theme/routes.
- Tái cấu trúc: phần giới thiệu đang đứng trước văn bản; proposal nằm chung
  component với quyết định/gallery, tự tải trình đọc khi gần viewport.
- Thiết kế lại: trưng bày quyết định trên điện thoại; gallery hiện chỉ có ảnh
  chính và dải thumbnail, modal thiếu trước/sau/vuốt/zoom/khóa cuộn nền.
- Tái sử dụng: Next Image, theme tokens, auth state, ProposalViewer, danh mục
  ảnh, metadata gốc, FeaturedAssets và các route hiện có.
- Rủi ro: CSS trang chủ chồng nhiều lần; cần giới hạn selector vào homepage,
  không tác động dashboard. Modal phải quản lý focus/cuộn; không tải PDF nặng
  trước thao tác. Không thay nội dung pháp lý, dữ liệu hay backend.

## Thiết kế và thứ tự

Hero → Văn bản thành lập → Gallery → Giới thiệu/sứ mệnh → Đề cử công bố → Hành
trình → Proposal → Cộng đồng/đồng hành → Footer chung.

Mobile 360–390px: nền giấy/đỏ nâu theo theme, serif hiện có cho heading, body
16px, gutter 16–20px, khoảng section 48–72px, điều khiển tối thiểu 44px. Desktop
mở rộng thành editorial split; không ép hero cao cả màn hình.

## Các lát triển khai / nghiệm thu

1. Sắp lại section và rút gọn hiển thị sứ mệnh; nội dung dài vẫn mở được.
   Verify: test thứ tự Hero/Quyết định/Gallery và auth CTA.
2. Trưng bày quyết định với preview thật, viewer hai trang/zoom, tải PDF và mở
   bằng browser dự phòng. Verify: focus, Escape, trang/zoom/loading/error.
3. Gallery ảnh lớn, tập thumbnail giới hạn, lọc đúng đếm từ dữ liệu, viewer
   trước/sau/vuốt/zoom, focus/scroll recovery. Verify: unit + Chrome touch.
4. Proposal preview gọn; chỉ import reader theo nút Xem tài liệu, giữ đầy đủ
   tính năng viewer cũ và đường dẫn PDF. Verify: không tải reader trước click.
5. Responsive/theme/accessibility và regression: 320/360/375/390/414/430/768/
   1024/1440px, guest/member, PDF/gallery lỗi, menu/footer/search.
6. Lint/typecheck/test/build, ảnh trước/sau và báo cáo kết quả thực đo.

Không thêm thư viện, không tạo ảnh AI, không thay backend, không deploy. Lệnh từ
repo: `npm.cmd --prefix frontend test -- --maxWorkers=2`,
`npm.cmd --prefix frontend run lint`, `npm.cmd --prefix frontend run typecheck`,
`npm.cmd --prefix frontend run build`.

## Giới hạn nghiệm thu

Chrome emulation không thay kiểm tra Safari iPhone/Android thật. Không tuyên bố
đạt p75 Core Web Vitals hay Lighthouse nếu chưa đo production theo điều kiện
tương ứng. Các kiểm thử API dùng fixture cục bộ, không giao dịch production.

## Kết quả bàn giao — 31/10/2026

### UI/UX đã triển khai

- Thứ tự mới: Hero → quyết định thành lập → gallery → giới thiệu/sứ mệnh → nhóm
  lĩnh vực/đề cử đã công bố → hành trình → proposal → cộng đồng → tài khoản và
  footer chung. Không có khối giới thiệu chen giữa Hero, quyết định, gallery.
- Hero gọn, không ép full-screen; logo header giữ nguyên, biểu trưng lớn chỉ
  dùng trên tablet/desktop. Nền trống đồng và chi tiết chim Lạc dùng asset thật,
  Next Image tối ưu theo kích thước hiển thị. Nội dung dài được giữ trong phần
  mở rộng/desktop; không thêm thành tích, đối tác hoặc tuyên bố thẩm quyền.
- Mobile: gutter 20px, section spacing 48–56px, body 16px; nút gửi hồ sơ/khám
  phá đủ chiều rộng và ít nhất 48px. Giữ navigation, auth state và theme chung.
- Văn bản: preview thật, metadata số 55/ngày 02/01/2026/VIDS giữ nguyên; viewer
  chỉ tải khi mở, đọc PDF gốc bằng PDF.js, chuyển cả hai trang và zoom. Có tải
  gốc, mở bằng trình duyệt, loading/error/timeout, đóng/Escape và trả focus.
- Gallery giữ 38 ảnh thật và nhóm hiện có; đếm trực tiếp từ dữ liệu. Ảnh lớn
  không cắt chủ thể; sáu thumbnail đại diện, bộ lọc ngang nằm trong viewport.
  Lightbox duyệt toàn bộ danh mục hiện chọn, vuốt/phím mũi tên/trước-sau, zoom,
  chú thích/số ảnh, khóa cuộn nền, focus trap/return, loading/error và thử lại.
- Giới thiệu và năm trọng tâm chuyển sang nội dung dễ quét, chi tiết mở rộng;
  giữ nguyên nội dung chuyên môn và nguyên tắc đồng hành.
- Đề cử vẫn lấy API công bố hiện có. Quan sát cả section để bắt đầu tải khi tiêu
  đề tiến gần viewport; giữ cache, loading, empty, error/retry và search.
- Proposal dùng bìa thật đúng tỉ lệ 1600×900, số trang từ danh mục hiện có; chỉ
  import trình đọc theo thao tác. Giữ chuyển trang, mục lục, zoom, fullscreen,
  bản chữ và PDF gốc. Nhạc không autoplay và dừng khi rời component.
- Không sửa backend, quyền, API, tài liệu gốc, gallery assets, liên hệ, SEO
  metadata hoặc route. Không push/merge/deploy production.

### File thuộc đợt trang chủ

| Nhóm               | File                                                                                                                                                                                      |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Layout/thứ tự      | `frontend/src/app/(public)/page.tsx`                                                                                                                                                      |
| Style riêng        | `frontend/src/components/public/home-editorial.css`                                                                                                                                       |
| Văn bản            | `institution-content.tsx`, `institution-document-preview.tsx`, `decision-document-viewer.tsx`                                                                                             |
| Modal chung        | `public-media-dialog.tsx`                                                                                                                                                                 |
| Gallery            | `heritage-gallery.tsx`, `heritage-lightbox.tsx`                                                                                                                                           |
| Nội dung/hiệu năng | `mission-content.tsx`, `heritage-symbols.tsx`, `featured-assets.tsx`, `deferred-proposal-viewer.tsx`, `welcome-music.tsx`                                                                 |
| Unit               | `app/home-page.test.tsx`, `public/heritage-gallery.test.tsx`, `public/institution-media.test.tsx`, `public/deferred-proposal-viewer.test.tsx`, `public/decision-document-viewer.test.tsx` |
| Browser            | `frontend/e2e/home-editorial.spec.ts`, `frontend/e2e/public-shell-layout.spec.ts`                                                                                                         |

Các tên file rút gọn trong bảng thuộc `frontend/src/components/public/`. Các
thay đổi dashboard/form/ví từ yêu cầu trước được giữ nguyên, không phải phạm vi
thiết kế lại trang chủ lần này.

### Kiểm chứng

- Full frontend checkpoint: **1.027 test / 240 file đạt**. Sau tinh chỉnh cuối,
  **72 test public/homepage / 17 file** chạy lại và đạt.
- **27 E2E đạt, 7 skip có điều kiện viewport**, Chrome desktop + Pixel 7
  emulation; runner exit 0. Bao gồm regression phiên guest/member, reload,
  refresh-only, logout/tab khác, header/menu/bottom navigation và featured API.
- Reflow: 320/360/375/390/414/430/768/1024/1440px, cả light/dark, hai project;
  không tràn ngang. Nút chính full width và cỡ chữ 16px có assertion riêng.
- **12 lượt axe không phát hiện vi phạm** với các tag WCAG A/AA đã chọn: tám
  trạng thái trang chủ, hai modal PDF, hai lightbox (mobile dùng dark).
- PDF gốc thực tế render cả trang 1 và 2; zoom 125%; fallback khi HTTP 503;
  gallery lọc/vuốt/keyboard/zoom/đóng, ảnh lỗi HTTP 503 và tải lại thành công;
  proposal mở theo click và điều khiển sang trang 2/53, zoom hoạt động.
- Không có request tải `decision.pdf` hoặc `proposal-2026.pdf` trong lượt duyệt
  trang chủ/đổi theme/scroll khi chưa bấm mở. Không tải 38 ảnh lớn đầu trang;
  thumbnail và ảnh lớn dùng kích thước Next Image riêng.
- Typecheck và production build đạt. ESLint toàn frontend không có lỗi, còn bốn
  warning có sẵn ở `membership-chat-access-admin.tsx`; lint các file trang chủ
  đã đổi đạt. Format và `git diff --check` đạt.
- Các lỗi test được sửa theo nguyên nhân: cập nhật giả định logo mobile sang
  logo header; dùng menu để đổi theme trên điện thoại; touch fixture có
  identifier; sửa CSS grid hai cột cũ làm hẹp CTA; sửa tuple test theo strict
  TS. Không tăng timeout hoặc bỏ quality gate.

### Ảnh và log cục bộ

`tmp/home-redesign-20261030/` chứa baseline và ảnh mới:

- `before-hero-light-390.png` / `after-hero-light-390.png`.
- `before-decision-dark-1440.png` / `after-decision-dark-1440.png`.
- `before-gallery-light-390.png` / `after-gallery-light-390.png`.
- Có các ảnh tương ứng cho cả hai theme và 390/1440px.
- `regression-final.log`, `build-verified.log`, `final-public.log`, `unit.log`.

Ảnh modal và footer: thư mục kết quả Playwright `frontend/test-results/`. Không
commit ảnh kiểm thử dung lượng lớn.

### Chưa chứng minh và bước tiếp theo

- Đã bỏ cách ẩn ảnh gallery bằng opacity chờ JavaScript/onLoad. Smoke tắt hoàn
  toàn JavaScript chưa đạt: public layout hiện có stream trong Suspense chờ
  auth; ảnh đã có opacity 1 nhưng vẫn nằm trong vùng ẩn `S:1` của Next và màn
  hình chỉ hiện “Đang tải nội dung…”. Không tuyên bố hỗ trợ toàn trang khi tắt
  JS; không sửa kiến trúc auth/layout dùng chung trong đợt homepage này.

- Chưa kiểm tra trên iPhone Safari/Android/tablet vật lý; pinch zoom native, bàn
  phím ảo, thay đổi address bar và xoay màn hình cần nghiệm thu thiết bị.
- Chưa kiểm thử screen reader đầy đủ, toàn bộ thao tác ở browser zoom 200%, mọi
  tổ hợp mạng yếu và mọi trang proposal. Điều khiển zoom viewer đã được test.
- Không có số Lighthouse hay RUM p75 trong đợt này; không tuyên bố đạt LCP
  2,5s/CLS 0,1/INP 200ms hoặc Performance 90. Tối ưu tải đã có assertion mạng,
  nhưng không thay thế đo hiệu năng production trên điều kiện kiểm soát.
- Thử nghiệm staging bằng tài khoản thật được cấp phép; đo Lighthouse mobile
  trên production build và RUM khi có lưu lượng trước khi kết luận Core Web
  Vitals.
