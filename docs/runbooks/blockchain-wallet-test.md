# Kiểm tra ví ký blockchain

## Trên production, không dùng hồ sơ thật

1. Đăng nhập bằng tài khoản `SUPER_ADMIN` đã được cấp quyền `blockchain.sign`.
2. Mở **Ký blockchain**, kết nối ví tổ chức đã được xác minh trên Polygon Mainnet.
3. Đối chiếu địa chỉ ví và mạng hiển thị trên trang với MetaMask.
4. Chọn **Kiểm tra ví ký** và xác nhận ký thông điệp kiểm tra trong ví.
5. Trang phải báo kiểm tra thành công. Nếu bị từ chối, sai địa chỉ, sai mạng hoặc
   ví mất `VERIFIER_ROLE`, dừng tại đây và xử lý đúng nguyên nhân.

Thao tác này dùng challenge hiện có: backend xác minh chữ ký của ví, quyền
`VERIFIER_ROLE` trên hợp đồng và tài khoản admin. Nó tạo bản ghi challenge/audit,
nhưng không tạo hồ sơ, không gửi giao dịch và không tiêu POL. Hàng đợi ký có thể
trống. Đây là phép thử kết nối và quyền ký, **không** chứng minh luồng ghi nhận
on-chain, xác nhận giao dịch hoặc thanh toán đã hoạt động.

## Kiểm tra giao dịch từ đầu đến cuối

Dùng môi trường riêng với cơ sở dữ liệu, ví, RPC và hợp đồng thử trên Polygon
Amoy; cấp `VERIFIER_ROLE` cho ví thử và dùng POL thử. Tạo hồ sơ tổng hợp trong
môi trường này, đi qua các bước đủ điều kiện ký rồi xác nhận giao dịch và đối
chiếu bằng chứng. Frontend hiện chỉ cấu hình Polygon Mainnet, nên cần cấu hình
Amoy và triển khai hợp đồng thử trước khi chạy quy trình này. Không dùng nút ký
hồ sơ trên production chỉ để thử ví: đó là giao dịch mainnet thật.
