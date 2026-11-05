import type { CmsGuideArticle } from "@/lib/api/types";
import { normalizeGuideSearch } from "@/components/guide/guide-search";

const CONTENT_DATE = "2026-11-05T00:00:00.000Z";

export const STARTER_GUIDES: CmsGuideArticle[] = [
  {
    id: "starter:account-basics",
    title: "Tạo tài khoản và bắt đầu sử dụng",
    slug: "huong-dan-bat-dau",
    summary: "Đăng ký, xác minh thư điện tử, đăng nhập và tìm các mục chính.",
    category: "getting-started",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 1,
    version: 1,
    readingMinutes: 3,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Tạo tài khoản</h2>
      <ol>
        <li>Mở <a href="/register">Đăng ký</a> và điền thông tin theo biểu mẫu.</li>
        <li>Mở hộp thư điện tử, tìm thư xác minh và bấm liên kết trong thư. Nếu chưa thấy, kiểm tra thư rác.</li>
        <li>Trở lại trang <a href="/login">Đăng nhập</a> bằng địa chỉ thư điện tử đã xác minh.</li>
      </ol>
      <h2>Tìm chức năng cần dùng</h2>
      <p>Sau khi đăng nhập, mở danh mục chính. Các mục thường dùng gồm Hồ sơ của tôi, Ví của tôi, Bằng xác lập, Cộng đồng và Hướng dẫn. Tên mục có thể khác đôi chút tùy quyền của tài khoản.</p>
      <h2>Quên mật khẩu hoặc không nhận được email</h2>
      <p>Dùng liên kết Quên mật khẩu trên trang đăng nhập để khôi phục quyền truy cập. Không gửi mật khẩu, mã xác minh hoặc liên kết khôi phục cho người khác.</p>
    `,
  },
  {
    id: "starter:dossier-submission",
    title: "Chuẩn bị và gửi hồ sơ đề cử",
    slug: "huong-dan-gui-ho-so",
    summary: "Chọn đúng loại hồ sơ, lưu bản nháp, kiểm tra tài liệu rồi gửi xét duyệt.",
    category: "dossiers",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 2,
    version: 1,
    readingMinutes: 5,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Trước khi tạo hồ sơ</h2>
      <ol>
        <li>Đăng nhập rồi mở <a href="/dossiers">Hồ sơ của tôi</a>. Kiểm tra xem hồ sơ tương tự đã có chưa để tránh gửi trùng.</li>
        <li>Chọn loại hồ sơ phù hợp và đọc kỹ mô tả, các trường bắt buộc cùng yêu cầu tài liệu đang hiển thị.</li>
        <li>Chuẩn bị thông tin đúng với chủ thể, tác phẩm và quyền sử dụng các tài liệu minh chứng.</li>
      </ol>
      <h2>Tạo và hoàn thiện bản nháp</h2>
      <ol>
        <li>Mở <a href="/dossiers/new">Tạo hồ sơ</a>, chọn loại hồ sơ rồi điền các trường theo biểu mẫu.</li>
        <li>Tải từng tài liệu vào đúng mục. Kiểm tra tên tệp, nội dung và giới hạn dung lượng hiển thị cạnh ô tải lên.</li>
        <li>Chọn tạo bản nháp. Chờ thông báo đã lưu, sau đó mở lại hồ sơ để chắc chắn nội dung và tài liệu còn đầy đủ.</li>
      </ol>
      <h2>Gửi để xét duyệt</h2>
      <p>Đọc lại thông tin và cảnh báo còn thiếu. Chọn Gửi hồ sơ khi mọi nội dung bắt buộc đã sẵn sàng. Ghi nhớ mã hồ sơ và kiểm tra trạng thái trong trang chi tiết sau khi gửi.</p>
      <h2>Lưu ý</h2>
      <p>Sau khi gửi, bạn vẫn có thể xem hồ sơ và lịch sử nhưng không thể tự chỉnh sửa. Hãy cập nhật khi được yêu cầu bổ sung.</p>
    `,
  },
  {
    id: "starter:dossier-follow-up",
    title: "Theo dõi trạng thái và bổ sung hồ sơ",
    slug: "huong-dan-theo-doi-ho-so",
    summary: "Đọc dòng thời gian, xử lý yêu cầu bổ sung và kiểm tra kết quả mới.",
    category: "dossiers",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 3,
    version: 1,
    readingMinutes: 4,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Mở đúng hồ sơ</h2>
      <p>Vào <a href="/dossiers">Hồ sơ của tôi</a>, tìm bằng tên hoặc mã hồ sơ rồi mở trang chi tiết. Dòng thời gian và thông báo cho biết hồ sơ đang ở bước nào.</p>
      <h2>Khi được yêu cầu bổ sung</h2>
      <ol>
        <li>Đọc toàn bộ nội dung yêu cầu và xác định trường hoặc tài liệu cần sửa.</li>
        <li>Chỉ cập nhật phần hệ thống mở cho phép chỉnh sửa. Tải lại minh chứng vào đúng mục và chờ xác nhận đã lưu.</li>
        <li>Đọc lại hồ sơ rồi chọn gửi bổ sung. Kiểm tra phiên bản, thời điểm gửi và trạng thái mới trong lịch sử.</li>
      </ol>
      <h2>Nếu chưa thấy trạng thái mới</h2>
      <p>Tải lại trang và xem lịch sử hồ sơ. Không tạo hồ sơ khác để thay thế hồ sơ đang được xử lý. Khi liên hệ hỗ trợ, cung cấp mã hồ sơ và mô tả bước đang vướng.</p>
    `,
  },
  {
    id: "starter:wallet-topup",
    title: "Nạp tiền vào ví và kiểm tra giao dịch",
    slug: "huong-dan-nap-tien-vao-vi",
    summary: "Nạp từ 5.000đ, thanh toán bằng mã QR và kiểm tra trạng thái giao dịch.",
    category: "wallet",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 4,
    version: 1,
    readingMinutes: 4,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Nạp tiền vào ví</h2>
      <ol>
        <li>Đăng nhập và mở <a href="/wallet">Ví của tôi</a>.</li>
        <li>Nhập số tiền muốn nạp, tối thiểu 5.000đ.</li>
        <li>Chọn Nạp tiền để xem mã QR và thông tin chuyển khoản.</li>
      </ol>
      <h2>Thanh toán</h2>
      <p>Quét mã QR bằng ứng dụng ngân hàng. Chuyển đúng số tiền và giữ nguyên nội dung chuyển khoản hiển thị. Yêu cầu có hiệu lực trong 10 phút. Số dư ví tăng sau khi thanh toán được xác nhận.</p>
      <h2>Chưa thấy tiền vào ví?</h2>
      <ol>
        <li>Kiểm tra lịch sử giao dịch ngân hàng để xem tiền đã được trừ chưa.</li>
        <li>Nếu yêu cầu đã hết hạn và bạn chưa chuyển tiền, hãy tạo yêu cầu mới.</li>
        <li>Nếu đã chuyển tiền, đừng thanh toán lần nữa. Mở yêu cầu hiện tại để kiểm tra trạng thái.</li>
        <li>Nếu tiền đã trừ nhưng trạng thái chưa đổi, liên hệ bộ phận hỗ trợ và cung cấp mã yêu cầu nạp hiển thị trong Ví của tôi.</li>
      </ol>
    `,
  },
  {
    id: "starter:certificate-verification",
    title: "Tra cứu và kiểm tra bằng xác lập",
    slug: "huong-dan-tra-cuu-bang-xac-lap",
    summary: "Tra cứu bằng mã hoặc mã QR và đối chiếu thông tin xác minh.",
    category: "verification",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 5,
    version: 1,
    readingMinutes: 3,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Cách tra cứu</h2>
      <ol>
        <li>Mở <a href="/verify">Tra cứu bằng xác lập</a>.</li>
        <li>Nhập mã trên bằng hoặc quét mã QR được cung cấp.</li>
        <li>Đối chiếu tên, chủ thể, thời điểm cấp và trạng thái đang hiển thị.</li>
      </ol>
      <h2>Nếu thông tin không khớp</h2>
      <p>Kiểm tra lại mã và thử quét mã QR trên bản gốc. Nếu vẫn không tìm thấy hoặc nội dung khác với bằng, lưu lại mã tra cứu và liên hệ đơn vị phát hành.</p>
      <h2>Phạm vi của bằng xác lập</h2>
      <p>Thông tin tra cứu giúp đối chiếu nội dung và trạng thái ghi nhận. Bằng xác lập không thay thế kết luận pháp lý hay giấy tờ chứng minh quyền sở hữu.</p>
    `,
  },
  {
    id: "starter:community",
    title: "Tham gia cộng đồng an toàn",
    slug: "huong-dan-tham-gia-cong-dong",
    summary: "Tìm bài viết, trao đổi đúng chủ đề và quản lý nội dung của bạn.",
    category: "community",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 6,
    version: 1,
    readingMinutes: 3,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Tìm nội dung phù hợp</h2>
      <ol>
        <li>Mở <a href="/community">Cộng đồng</a> và chọn chủ đề hoặc cách sắp xếp bài viết.</li>
        <li>Dùng ô tìm kiếm để thu hẹp kết quả, rồi mở bài viết để đọc đầy đủ và xem hình ảnh.</li>
        <li>Đăng nhập nếu muốn đăng bài, bình luận hoặc tương tác.</li>
      </ol>
      <h2>Đăng bài rõ ràng</h2>
      <p>Chọn đúng chủ đề, đặt tiêu đề mô tả nội dung và chỉ chia sẻ hình ảnh, tài liệu bạn có quyền sử dụng. Không đăng mật khẩu, mã xác thực, số tài khoản hoặc dữ liệu riêng tư của người khác.</p>
      <h2>Báo cáo nội dung cần xem xét</h2>
      <p>Dùng chức năng báo cáo trên bài viết hoặc bình luận khi gặp nội dung vi phạm. Tránh đăng lại thông tin cá nhân trong phần trao đổi công khai.</p>
    `,
  },
  {
    id: "starter:install-app",
    title: "Cài Tinh Hoa Việt lên thiết bị",
    slug: "huong-dan-cai-ung-dung",
    summary: "Cài ứng dụng lên Android, iPhone, iPad hoặc máy tính.",
    category: "install",
    audiences: ["PUBLIC"],
    status: "PUBLISHED",
    sortOrder: 7,
    version: 1,
    readingMinutes: 3,
    publishedAt: CONTENT_DATE,
    createdAt: CONTENT_DATE,
    updatedAt: CONTENT_DATE,
    bodyHtml: `
      <h2>Android hoặc máy tính</h2>
      <p>Mở trang bằng Chrome hoặc Edge trên thiết bị muốn cài. Chọn <a href="/install">Cài ứng dụng</a>; nếu trình duyệt hỗ trợ, xác nhận trong cửa sổ cài đặt. Sau đó mở biểu tượng Tinh Hoa Việt từ màn hình chính hoặc danh sách ứng dụng.</p>
      <h2>iPhone hoặc iPad</h2>
      <ol>
        <li>Mở trang web bằng Safari.</li>
        <li>Chạm nút Chia sẻ rồi chọn Thêm vào Màn hình chính.</li>
        <li>Chạm Thêm để xác nhận. Biểu tượng sẽ xuất hiện trên Màn hình chính.</li>
      </ol>
      <h2>Không thấy lời mời cài đặt?</h2>
      <p>Trình duyệt chỉ mở lời mời cài đặt khi thiết bị và ứng dụng đáp ứng điều kiện của nền tảng. Mở trang hướng dẫn cài đặt để xem tùy chọn của trình duyệt trên thiết bị.</p>
    `,
  },
];

export function getStarterGuide(slug: string): CmsGuideArticle | undefined {
  return STARTER_GUIDES.find((article) => article.slug === slug);
}

export function matchesStarterGuide(
  article: CmsGuideArticle,
  query: string,
  category: string,
): boolean {
  if (category && article.category !== category) return false;
  const normalizedQuery = normalizeGuideSearch(query);
  if (!normalizedQuery) return true;
  const content = article.bodyHtml.replace(/<[^>]*>/g, " ");
  return normalizeGuideSearch(`${article.title} ${article.summary} ${content}`).includes(
    normalizedQuery,
  );
}
