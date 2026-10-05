# Phản hồi khi tải trên mobile

## Mục tiêu

Người dùng thấy phản hồi ngay khi chuyển trang công khai hoặc khu vực làm việc, khi danh sách đang lấy dữ liệu và khi video chờ phát. Phản hồi cần dễ nhìn ở giao diện sáng, tối và không làm chậm thiết bị mobile.

## Phạm vi và tiêu chí

- `loading.tsx` cung cấp fallback cho lần mở đầu và các lần chuyển trang trong nhóm công khai, khu vực làm việc.
- Skeleton giữ vị trí nội dung chính, có nhãn trạng thái tiếng Việt, không chặn thao tác trên phần giao diện còn dùng được.
- Skeleton của tìm kiếm, thư viện và chi tiết tác phẩm nhìn thấy ở cả hai giao diện.
- Video chỉ hiện biểu tượng tải khi đã bắt đầu phát mà còn chờ dữ liệu; hết chờ thì biểu tượng biến mất.
- Chuyển động giảm hoặc tắt khi hệ thống yêu cầu giảm chuyển động.

## Cách triển khai

Next.js App Router 16 dùng `loading.tsx` cho fallback của route segment. Các truy vấn phía trình duyệt tiếp tục dùng trạng thái `isPending` hiện có. CSS dùng token `--theme-*` và chỉ hoạt ảnh opacity/transform nhẹ. Không thêm thư viện.

Ví dụ quy ước:

```tsx
if (query.isPending) return <ContentSkeleton />;
```

## Thứ tự công việc

1. Tạo fallback tải dùng chung và gắn vào root, nhóm công khai, nhóm dashboard.
2. Chỉnh skeleton dữ liệu hiện có theo token sáng/tối và nhãn truy cập.
3. Thêm spinner cho trạng thái video đang đệm; tải trước video khi gần màn hình và giữ bộ đệm khi bấm phát.
4. Kiểm tra ở màn hình mobile, chạy test, lint, typecheck và build.

## Lệnh kiểm tra

```bash
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

## Giới hạn

Video gần vùng nhìn thấy được tải đệm MP4 và tái sử dụng bộ đệm khi người dùng bấm phát. Bỏ qua tải đệm nếu bật tiết kiệm dữ liệu hoặc đang dùng kết nối 2G. Nếu MP4 chưa phát được sau ba giây, thử luồng HLS. Trình duyệt iOS có thể hạn chế `preload`; khi đó video vẫn tải sau thao tác phát.

Fallback chỉ xuất hiện khi thực sự có tác vụ chờ; trang đã có dữ liệu tức thì có thể không kịp hiển thị skeleton.
