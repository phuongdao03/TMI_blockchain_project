# Hướng dẫn chấm công và cấu hình địa điểm

## Dành cho Super Admin

1. Vào **Điểm chấm công**, tạo địa điểm với mã và tên dễ nhận biết. Kích hoạt địa điểm trước khi tạo chính sách hoặc phân công nhân viên.
2. Ở **Thiết lập vùng chấm công**, nhập ngày hiệu lực và múi giờ IANA của chính địa điểm, ví dụ `Asia/Ho_Chi_Minh`. Không dùng múi giờ của máy admin cho nhân viên ở nước khác.
3. Để đặt tâm vùng, có ba cách: tìm địa chỉ đầy đủ rồi chọn một kết quả và bấm **Chọn vị trí này làm tâm vùng**; đứng tại điểm làm việc và bấm **Lấy vị trí thiết bị tại văn phòng**; hoặc nhập cặp vĩ độ/kinh độ đã xác minh. Chọn thành phố chỉ di chuyển bản đồ, không tự đổi tâm vùng.
4. Geocoding có thể trả vị trí gần đúng, nhất là tại tòa nhà lớn hoặc địa chỉ mới. Kiểm tra bằng bản đồ, tọa độ và bằng chứng ngoài hệ thống trước khi lưu. Vị trí thiết bị cũng kèm sai số do trình duyệt báo; không coi kết quả GPS là chính xác tuyệt đối.
5. Nhập bán kính cho phép và sai số GPS tối đa theo điều kiện thực tế. Xem lại vùng tròn, ngày hiệu lực và múi giờ, rồi lưu chính sách. Phân công nhân viên cho đúng địa điểm và giai đoạn.
6. Theo dõi chấm công tại tài khoản Super Admin. Bằng chứng vị trí chính xác chỉ dành cho người có quyền, không xuất ra báo cáo chung. Trường hợp ngoài vùng/sai số lớn phải xử lý theo quy trình xét duyệt hiện hành; không sửa bằng chứng cũ.

### Nếu bản đồ không tải

- Kiểm tra website chạy HTTPS và `Referrer-Policy` trên trang là `strict-origin-when-cross-origin`, không có `no-referrer` trên trang cấu hình.
- Trong Stadia Maps, khai báo đúng domain `decu.tinhhoaviet.org.vn`. Kiểm tra tile request trong DevTools → Network: trạng thái thành công, `Referer` là domain production. Không gửi API key trong ảnh chụp.
- URL tile là biến build-time `NEXT_PUBLIC_OSM_TILE_URL`. Không thêm `api_key` vào URL công khai. Nếu tile vẫn lỗi, dùng tọa độ đã xác minh để làm việc tạm thời và báo quản trị kỹ thuật; không đoán vị trí bằng bản đồ trắng.
- Tìm địa chỉ dùng `STADIA_MAPS_API_KEY` ở backend; nếu thiếu key hoặc nhà cung cấp không trả kết quả, ô tìm kiếm sẽ báo lỗi nhưng vẫn có thể nhập tọa độ thủ công.

## Dành cho nhân viên

1. Dùng Chrome/Safari trên điện thoại, mở website qua HTTPS và đăng nhập tài khoản nhân viên đã được liên kết hồ sơ nhân sự.
2. Bật dịch vụ vị trí của điện thoại; cho phép trình duyệt dùng vị trí **khi sử dụng website**. Không cần bật theo dõi vị trí liên tục.
3. Vào **Chấm công** và bấm **Chấm công vào** hoặc **Chấm công ra**. Hệ thống lấy một mẫu GPS khi bạn chủ động bấm nút; chờ thông báo kết quả rồi kiểm tra giờ vào/ra và trạng thái. Không bấm liên tục khi đang chờ.
4. Nếu trình duyệt từ chối quyền, vào cài đặt quyền của website và điện thoại để cho phép vị trí rồi thử lại. Nếu quá thời gian hoặc sai số lớn, di chuyển tới chỗ thoáng, bật định vị chính xác, kiểm tra kết nối mạng và thử lại. Không dùng địa chỉ tìm kiếm của admin thay cho GPS chấm công.
5. Nếu kết quả đang chờ xét duyệt vị trí, liên hệ người quản lý; không xem đó là ngày công đã được duyệt. Chỉ nhân viên và Super Admin có quyền mới xem bằng chứng GPS chi tiết; tọa độ không xuất trong báo cáo chung.

## Kiểm tra trước khi mở production

- Kiểm tra tile thật trên Chrome và Safari, desktop và điện thoại, ở domain production.
- Kiểm tra tìm địa chỉ bằng tài khoản Super Admin thật; tài khoản khác phải bị từ chối. Đảm bảo key chỉ nằm trong biến môi trường backend.
- Tại ít nhất một điểm làm việc thực tế, đối chiếu địa chỉ tìm kiếm, tọa độ, bán kính, sai số GPS và chấm công vào/ra của thiết bị thử nghiệm. Không dùng dữ liệu lương thật để kiểm thử.
