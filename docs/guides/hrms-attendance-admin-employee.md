# Hướng dẫn thiết lập điểm làm việc và chấm công

Tài liệu này dành cho quản trị viên thiết lập vùng chấm công và nhân viên ghi nhận giờ vào, giờ ra. Chấm công dùng vị trí tại thời điểm nhân viên chủ động thao tác; kết quả ngoài vùng hoặc có sai số lớn cần được xem xét theo quy trình của tổ chức.

## Quản trị viên: thiết lập điểm làm việc

**Trước khi bắt đầu:** Chuẩn bị địa chỉ, múi giờ, tọa độ đã kiểm tra (nếu có), bán kính chấm công và ngày bắt đầu áp dụng. Đăng nhập bằng tài khoản Super Admin.

1. Mở **Điểm chấm công** tại `/admin/attendance/worksites`. Tạo điểm mới với mã và tên dễ nhận biết, rồi kích hoạt.
2. Trong **Thiết lập vùng chấm công**, chọn múi giờ của chính điểm làm việc, chẳng hạn `Asia/Ho_Chi_Minh`. Đối với địa điểm ở múi giờ khác, dùng múi giờ của địa điểm đó.
3. Xác định tâm vùng bằng một trong ba cách: tìm địa chỉ đầy đủ rồi chọn **Chọn vị trí này làm tâm vùng**; dùng **Lấy vị trí thiết bị tại văn phòng** khi đang đứng tại đó; hoặc nhập vĩ độ và kinh độ đã xác minh. Chỉ chọn thành phố trên bản đồ sẽ không đặt tâm vùng.
4. Kiểm tra vị trí trên bản đồ với địa chỉ thực tế. Kết quả tìm địa chỉ và GPS thiết bị đều có thể sai lệch; xem tọa độ và sai số trước khi lưu.
5. Nhập bán kính, sai số GPS tối đa và ngày hiệu lực. Kiểm tra lại vùng trên bản đồ và múi giờ, lưu chính sách, rồi phân công nhân viên cho đúng điểm làm việc và giai đoạn.
6. Mở khu vực theo dõi chấm công để đối chiếu giờ vào, giờ ra. Xem bằng chứng vị trí trước khi xử lý trường hợp ngoài vùng hoặc sai số lớn. Không sửa bằng chứng đã ghi nhận.

**Kiểm tra kết quả:** Điểm làm việc đang hoạt động, chính sách có ngày hiệu lực đúng và nhân viên xuất hiện trong danh sách được phân công. Tọa độ chi tiết chỉ dành cho người có quyền; báo cáo chung không xuất bằng chứng GPS chi tiết.

### Khi bản đồ hoặc ô tìm địa chỉ không hoạt động

- **Bản đồ trống:** Kiểm tra website đang chạy qua HTTPS. Người vận hành kỹ thuật kiểm tra cấu hình Stadia Maps cho domain `decu.tinhhoaviet.org.vn`, chính sách `Referrer-Policy` và yêu cầu tải tile trong Network của trình duyệt. Biến `NEXT_PUBLIC_OSM_TILE_URL` là cấu hình lúc build; không đặt API key vào URL công khai.
- **Không tìm được địa chỉ:** Người vận hành kỹ thuật kiểm tra `STADIA_MAPS_API_KEY` ở backend và phản hồi của nhà cung cấp. Trong lúc chờ xử lý, có thể nhập tọa độ đã xác minh. Không ước lượng tâm vùng từ một bản đồ trống.
- **GPS thiết bị thiếu chính xác:** Kiểm tra vị trí thực tế và sai số trình duyệt trả về. Không dùng kết quả tìm địa chỉ để thay thế bằng chứng chấm công của nhân viên.

## Nhân viên: chấm công vào và ra

**Trước khi bắt đầu:** Đăng nhập tài khoản đã liên kết hồ sơ nhân sự, mở website qua HTTPS trên điện thoại và cho phép trình duyệt dùng vị trí khi bạn chấm công.

1. Đến điểm làm việc được phân công và mở **Chấm công** tại `/attendance`.
2. Bật vị trí trên điện thoại. Khi trình duyệt hỏi quyền, chọn cho phép dùng vị trí trong lúc sử dụng website.
3. Bấm **Chấm công vào** hoặc **Chấm công ra**. Chờ thông báo kết quả; không bấm lặp lại khi yêu cầu đang xử lý.
4. Kiểm tra giờ và trạng thái mới hiển thị trên trang. Nếu bản ghi đang chờ xét duyệt vị trí, liên hệ người quản lý và chờ kết quả; chưa xem đó là ngày công được duyệt.

Hệ thống lấy vị trí khi bạn chủ động bấm nút; bạn không cần bật theo dõi vị trí liên tục. Bằng chứng GPS chi tiết chỉ hiển thị cho bạn và người quản trị có quyền.

### Nếu chấm công không thành công

- **Trình duyệt từ chối vị trí:** Mở quyền vị trí của website và điện thoại, cấp lại quyền rồi thử một lần nữa.
- **Hết thời gian hoặc sai số quá lớn:** Kiểm tra kết nối mạng, bật định vị chính xác và di chuyển tới nơi thoáng hơn trước khi thử lại.
- **Ngoài vùng làm việc:** Kiểm tra bạn đang ở đúng điểm được phân công. Nếu vẫn có sai lệch, báo người quản lý để xét duyệt theo bằng chứng; không dùng địa chỉ tìm kiếm thay cho vị trí thực tế.

## Kiểm tra trước khi áp dụng tại địa điểm mới

- Kiểm tra bản đồ và tìm địa chỉ trên thiết bị thực tế, với tài khoản Super Admin và domain sử dụng thật.
- Đối chiếu tọa độ, bán kính, sai số GPS, ngày hiệu lực và múi giờ với địa điểm làm việc.
- Thử chấm công vào và ra bằng tài khoản thử nghiệm đã được phân công. Xác nhận trạng thái và quyền xem bằng chứng vị trí trước khi áp dụng cho nhân viên.
