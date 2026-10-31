# Điều hướng Tinh Hoa Việt — 31/10/2026

## Phạm vi và kiểm kê

Kế thừa danh sách 97 trang trong `UIUX_AUDIT.md`; các URL, guard và chuyển hướng
hiện hữu được giữ nguyên. Nguồn kiểm kê: `app/**/page.tsx`,
`role-workspaces.ts`, `release-mode.ts`, `dashboard-navigation.tsx` và các
layout RoleGate. Không thêm API hay quyền.

| Ngữ cảnh   | Đường dẫn                                                                  | Điều kiện                                            | Điểm vào                         |
| ---------- | -------------------------------------------------------------------------- | ---------------------------------------------------- | -------------------------------- |
| Công khai  | /, /works, /works/[slug], /community, /verify                              | Mọi người                                            | Header, drawer, thanh dưới       |
| Giới thiệu | /#gioi-thieu, /#van-ban-thanh-lap, /#thu-vien-anh, /#muc-tieu-chuong-trinh | Mọi người                                            | Nhóm Về Tinh Hoa Việt            |
| Tham gia   | /process, /cong-dong/hoi-vien, /dossiers/new                               | Hồ sơ: USER hoặc khách qua đăng nhập; ẩn khi preview | Drawer, thanh dưới               |
| Hỗ trợ     | /guide, /install, /policies, /policies#privacy, /#lien-he                  | Mọi người                                            | Drawer, footer                   |
| Cá nhân    | /workspace, /account, /notifications, /activity, /community/mine           | Phiên đăng nhập; guard hiện hữu                      | Menu tài khoản, workspace        |
| Hồ sơ      | /dossiers, /certificates và trang con                                      | USER; giới hạn preview hiện hữu                      | Nhóm hồ sơ                       |
| Dịch vụ    | /wallet, /membership, /vouchers, /advertising                              | Giữ điều kiện customer/capability hiện hữu           | Nhóm dịch vụ                     |
| Thẩm định  | /reviews, /work-allocations và trang con                                   | MODERATOR; guard hiện hữu                            | Nhóm công việc, thanh dưới riêng |
| Nhân sự    | /attendance, /leave, /overtime                                             | Điều kiện nhân viên hiện hữu                         | Drawer workspace                 |
| Quản trị   | /admin/\*\*                                                                | SUPER_ADMIN hoặc capability theo từng mục            | Nhóm quản trị có lọc quyền       |

## Thiết kế và thứ tự thực hiện

1. Cấu hình công khai dùng chung; matcher theo ranh giới URL, không nhận nhầm
   tiền tố.
2. Header mobile logo + tìm kiếm + menu. Desktop rút gọn liên kết, nhóm giới
   thiệu mở bằng click/bàn phím.
3. Thanh dưới tối đa năm mục: Trang chủ, Khám phá, Gửi hồ sơ, Cộng đồng, Cá
   nhân. Không hiển thị hành động hồ sơ khi thiếu quyền hoặc preview.
4. Drawer chia Khám phá / Về Tinh Hoa Việt / Tham gia / Hỗ trợ / Tài khoản; khóa
   cuộn, giữ focus, đóng khi điều hướng hoặc phiên thay đổi.
5. Tìm kiếm dùng autocomplete và `/works?query=`, tách khỏi tra cứu bằng xác
   lập.
6. Workspace thẩm định có thanh công việc riêng; quyền đa vai trò được cộng thêm
   thay vì mất theo persona ưu tiên. Nhóm quản trị thu gọn được, tự mở nhóm đang
   hoạt động.
7. Breadcrumb trang con; giữ autosave hồ sơ, cảnh báo khi bản chưa lưu không thể
   sao lưu.
8. Kiểm tra chức năng, responsive 320–1440, hai theme, phiên và quyền. Báo cáo
   chỉ ghi kết quả thực chạy; dữ liệu QA là fixture cục bộ.

## Tiêu chí nghiệm thu

Không tràn ngang, vùng chạm tối thiểu 44px, nhãn thanh dưới không bị cắt. Mỗi
thanh có tối đa một mục hiện hành. Escape, Tab/Shift+Tab, backdrop, back/forward
và anchor hoạt động. Không thay đổi backend, dữ liệu, guard hoặc điều kiện quyền
nghiệp vụ.

## Kết quả kiểm chứng

Đã triển khai và kiểm chứng cục bộ. Build/typecheck/lint đạt; checkpoint toàn
frontend 1.033 test đạt, 63 ca liên quan xác nhận lại sau tinh chỉnh cuối. E2E
cuối hợp nhất 24 đạt / 4 viewport skip / 0 lỗi; 72 cấu hình responsive, 16 scan
axe không vi phạm. Xem [báo cáo 14 mục](NAVIGATION_REDESIGN_REPORT_2026.md) và
[kiểm kê 97 route](NAVIGATION_ROUTE_AUDIT_2026.md). Chưa nghiệm thu thiết bị
thật hoặc toàn bộ API staging.
