# Spec: Trang tìm kiếm đề cử theo hướng album

## Objective

Đưa tác phẩm về trung tâm của trang `/search`: kết quả hiển thị như các bìa album có thể mở trực tiếp trang chi tiết; bộ tinh chỉnh chỉ mở khi người dùng cần. Thành công khi không còn cột bộ lọc cố định chiếm chiều ngang desktop và mọi điều kiện tìm kiếm hiện tại vẫn được giữ trên URL.

## Tech stack và lệnh kiểm tra

- Next.js 16, React 19, TypeScript, TanStack Query, Vitest.
- Test: `npm.cmd --prefix frontend test -- --run src/components/search/search-results-page.test.tsx`
- Lint: `npm.cmd --prefix frontend run lint`
- Typecheck: `npm.cmd --prefix frontend run typecheck`
- Build: `npm.cmd --prefix frontend run build`

## Cấu trúc và phong cách

- Trang: `frontend/src/components/search/search-results-page.tsx`.
- Bộ lọc: `frontend/src/components/search/search-filters.tsx`.
- Kiểm thử: các tệp `.test.tsx` cùng thư mục.
- Sử dụng token màu THV và thẻ `<Link>` cho toàn bộ tile; không thay đổi API hoặc cấu trúc dữ liệu backend.

## Chiến lược kiểm thử

- Unit/component: xác nhận lưới album, liên kết chi tiết, bộ tinh chỉnh và URL filter không đổi.
- Browser: desktop và mobile; kiểm tra drawer bộ lọc, trạng thái focus, console và tương phản.

## Boundaries

- Always: giữ liên kết, truy vết search click, URL filter, keyboard/Escape cho drawer.
- Ask first: thay đổi API search, schema hay dependency.
- Never: thêm mock data, bỏ trạng thái lỗi/rỗng hoặc xóa test hiện có.

## Success criteria

1. Kết quả chiếm toàn bộ chiều rộng nội dung và hiển thị thành lưới album đáp ứng.
2. Desktop không có cột bộ lọc cố định; bộ tinh chỉnh mở theo yêu cầu.
3. Mỗi tile có liên kết chi tiết, danh mục, thông tin công bố và trạng thái chứng thư khi có.
4. Mobile vẫn dùng drawer có quản lý focus và Escape để đóng.
