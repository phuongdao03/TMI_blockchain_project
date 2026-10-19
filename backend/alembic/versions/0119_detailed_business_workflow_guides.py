"""Add source-checked step-by-step business workflow guides.

Revision ID: 0119_business_guides
Revises: 0118_personal_account_guide
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0119_business_guides"
down_revision: str | None = "0118_personal_account_guide"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _search(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


# Route labels, status transitions and guards were checked against the dossier,
# payment, review, work-allocation and HR workspaces and their backend services.
_GUIDES = (
    (
        "applicant-process-overview",
        "Toàn bộ quy trình tham gia và nộp hồ sơ",
        "Từ chuẩn bị hồ sơ đến thẩm định, thanh toán theo yêu cầu và nhận kết quả.",
        "dossiers",
        ("USER",),
        30,
        """
        <h2>Trước khi bắt đầu</h2><p>Đăng nhập bằng tài khoản có quyền gửi hồ sơ.
        Mở <a href="/dossiers">Hồ sơ của tôi</a> để xem hồ sơ đã có, tránh tạo trùng.
        Loại hồ sơ quyết định các trường và tài liệu cần chuẩn bị; hãy xem yêu cầu
        hiển thị sau khi chọn loại, vì biểu mẫu có thể được cập nhật.</p>
        <h2>Tiến trình</h2><ol>
        <li><strong>Chuẩn bị:</strong> chọn loại hồ sơ, đọc các trường bắt buộc và
        quy định tài liệu; chuẩn bị thông tin đúng với chủ thể và tác phẩm.</li>
        <li><strong>Tạo bản nháp:</strong> nhập tên, mô tả và trường theo loại hồ sơ;
        chọn Tạo hồ sơ nháp. Mở bản nháp để hoàn thiện thông tin và minh chứng.</li>
        <li><strong>Gửi:</strong> kiểm tra nội dung, tài liệu và trạng thái lưu;
        chọn nút gửi hồ sơ. Sau khi gửi, phiên bản nộp được ghi nhận và hồ sơ
        chuyển khỏi Bản nháp.</li>
        <li><strong>Chờ xử lý:</strong> theo dõi trạng thái và lịch sử trong chi tiết
        hồ sơ. Bộ phận tiếp nhận, người thẩm định và người quyết định xử lý theo
        từng giai đoạn; người nộp không cần gửi lại khi chưa có yêu cầu.</li>
        <li><strong>Bổ sung nếu được yêu cầu:</strong> đọc nội dung yêu cầu, sửa
        bản được mở cho chỉnh sửa, tải lại minh chứng cần thiết rồi gửi lại.</li>
        <li><strong>Thanh toán nếu phát sinh:</strong> chỉ khi hồ sơ được phê duyệt
        và có yêu cầu phí, màn hình hồ sơ mới hiển thị khoản cần thanh toán.
        Kiểm tra khoản phí và trạng thái giao dịch trước khi thao tác.</li>
        <li><strong>Nhận kết quả:</strong> theo dõi các bước phát hành; mở
        <a href="/certificates">Bằng xác lập</a> khi bằng đã được cấp.</li>
        </ol><h2>Khi nào hoàn tất?</h2><p>Hồ sơ hiển thị kết quả xử lý hoặc
        bằng xác lập đã phát hành. Phê duyệt chưa đồng nghĩa thanh toán xong;
        thanh toán xong chưa đồng nghĩa bằng đã phát hành. Trạng thái bị từ chối,
        hủy hoặc thu hồi cần xem lý do và hướng dẫn trên chính hồ sơ.</p>
        <h2>Bài theo từng bước</h2><p>Xem
        <a href="/help/prepare-dossier">chuẩn bị</a>,
        <a href="/help/create-dossier-draft">tạo bản nháp</a>,
        <a href="/help/submit-dossier">gửi hồ sơ</a>,
        <a href="/help/dossier-status-and-supplement">theo dõi và bổ sung</a>,
        <a href="/help/dossier-payment-guide">thanh toán</a>.</p>
        """,
    ),
    (
        "prepare-dossier",
        "Chuẩn bị thông tin và tài liệu trước khi tạo hồ sơ",
        "Xác định loại hồ sơ, trường bắt buộc và minh chứng theo biểu mẫu hiện hành.",
        "dossiers",
        ("USER",),
        31,
        """
        <h2>Bắt đầu ở đâu?</h2><p>Mở <a href="/dossiers/new">Tạo hồ sơ</a>.
        Bạn cần đăng nhập bằng tài khoản có quyền gửi hồ sơ.</p>
        <h2>Kiểm tra trước khi nhập</h2><ol>
        <li>Ở bước Chọn loại, tìm loại phù hợp và đọc mô tả. Mỗi loại dùng
        biểu mẫu riêng; không chọn loại chỉ vì tên gần giống.</li>
        <li>Xem số trường thông tin bắt buộc và quy tắc tài liệu được hiển thị
        cho loại vừa chọn. Chuẩn bị tên, mô tả, thông tin chủ thể và dữ liệu
        tương ứng với các trường đó.</li>
        <li>Chuẩn bị tệp minh chứng đúng mục đích, đọc loại tệp và giới hạn
        hiển thị trong từng ô tải lên. Giữ bản gốc để đối chiếu khi được yêu cầu.</li>
        <li>Kiểm tra quyền sử dụng tài liệu và nội dung sẽ công khai. Chỉ gửi
        thông tin mà bạn có thể xác nhận là đúng.</li></ol>
        <h2>Kiểm tra kết quả</h2><p>Bạn đã chọn được loại hồ sơ và có đủ dữ liệu
        cho các ô bắt buộc. Trang hiển thị tiến độ khai thông tin để bạn nhận
        ra phần còn thiếu trước khi tạo bản nháp.</p>
        <h2>Nếu chưa biết cần tệp nào</h2><p>Chọn loại hồ sơ trước. Danh sách
        tài liệu phụ thuộc vào phiên bản biểu mẫu đang áp dụng; đừng dựa vào
        danh sách của một hồ sơ cũ.</p>
        """,
    ),
    (
        "create-dossier-draft",
        "Tạo và hoàn thiện bản nháp hồ sơ",
        "Nhập đúng biểu mẫu, tạo bản nháp, lưu thông tin và tải minh chứng.",
        "dossiers",
        ("USER",),
        32,
        """
        <h2>Điều kiện</h2><p>Đã chọn loại hồ sơ và chuẩn bị dữ liệu theo
        <a href="/help/prepare-dossier">hướng dẫn chuẩn bị</a>.</p>
        <h2>Các bước</h2><ol>
        <li>Mở <a href="/dossiers/new">Tạo hồ sơ</a>, chọn loại hồ sơ. Kiểm tra
        tên loại và số trường bắt buộc trước khi đi tiếp.</li>
        <li>Nhập tên hồ sơ, mô tả và từng trường đang xuất hiện. Dấu bắt buộc
        và lựa chọn trong từng trường do biểu mẫu hiện hành quyết định.</li>
        <li>Kiểm tra chỉ báo tiến độ khai thông tin và lỗi cạnh từng ô; sửa
        dữ liệu trước khi chọn <strong>Tạo hồ sơ nháp</strong>.</li>
        <li>Trong trang chi tiết bản nháp, tiếp tục điền thông tin, chọn phạm vi
        hiển thị nếu được cung cấp và tải tài liệu vào đúng mục. Chờ thông báo
        đã lưu trước khi đóng trang hoặc chuyển sang bước khác.</li>
        <li>Mở lại hồ sơ trong <a href="/dossiers">Hồ sơ của tôi</a> để xác
        nhận tên, nội dung và tệp đều có mặt.</li></ol>
        <h2>Kết quả</h2><p>Hồ sơ mang trạng thái Bản nháp. Chỉ khi kiểm tra đủ
        thông tin và tệp, bạn mới thực hiện bước gửi để xét duyệt.</p>
        <h2>Nếu chưa tạo được</h2><p>Xem trường bị báo lỗi, nhất là trường bắt
        buộc và loại hồ sơ. Nếu đã mở bản nháp nhưng thay đổi chưa lưu, chờ
        trạng thái lưu hoặc thử lại trước khi gửi.</p>
        """,
    ),
    (
        "submit-dossier",
        "Kiểm tra và gửi hồ sơ để xét duyệt",
        "Gửi bản nháp hoặc hồ sơ đã bổ sung và kiểm tra phiên bản được ghi nhận.",
        "dossiers",
        ("USER",),
        33,
        """
        <h2>Trước khi gửi</h2><p>Hồ sơ phải đang là Bản nháp hoặc Cần bổ sung,
        đủ thông tin và minh chứng bắt buộc. Mở <a href="/dossiers">Hồ sơ của
        tôi</a>, chọn đúng hồ sơ theo tên và mã.</p>
        <h2>Các bước</h2><ol>
        <li>Đọc lại thông tin, tài liệu và phạm vi hiển thị. Kiểm tra các cảnh
        báo còn thiếu; chờ phần thông tin tự lưu xong.</li>
        <li>Ở cuối trang chi tiết, chọn nút gửi hồ sơ. Nếu đang ở Cần bổ sung,
        đọc yêu cầu và kiểm tra mọi phần đã sửa trước khi gửi lại.</li>
        <li>Chờ kết quả trên trang. Kiểm tra mã hồ sơ, thời điểm gửi, phiên bản
        mới và trạng thái sau gửi. Xem lại lịch sử để xác nhận lần gửi này.</li>
        </ol><h2>Sau khi gửi</h2><p>Hồ sơ không còn mở chỉnh sửa như Bản nháp.
        Bộ phận tiếp nhận xử lý tiếp. Chỉ sửa khi hệ thống chuyển sang Cần bổ
        sung và mở quyền chỉnh sửa cho phiên bản đó.</p>
        <h2>Vì sao nút gửi không hoạt động?</h2><p>Thường còn thông tin hoặc
        tài liệu bắt buộc, hoặc thay đổi chưa lưu xong. Đọc cảnh báo trên trang,
        hoàn thiện phần thiếu rồi thử lại; không tạo hồ sơ thứ hai để né lỗi.</p>
        """,
    ),
    (
        "dossier-status-and-supplement",
        "Theo dõi trạng thái và bổ sung hồ sơ",
        "Hiểu người đang xử lý, việc cần làm và cách gửi lại khi có yêu cầu.",
        "dossiers",
        ("USER",),
        34,
        """
        <h2>Đọc trạng thái ở đâu?</h2><p>Mở <a href="/dossiers">Hồ sơ của tôi</a>,
        chọn hồ sơ và xem nhãn trạng thái, dòng thời gian cùng lịch sử phiên bản.
        Thông báo trong <a href="/notifications">Thông báo</a> giúp nhận biết
        thay đổi, nhưng trang hồ sơ là nơi kiểm tra dữ liệu và thao tác.</p>
        <h2>Trạng thái và việc của bạn</h2><ul>
        <li><strong>Bản nháp:</strong> bạn còn được sửa; hoàn thiện và gửi.</li>
        <li><strong>Đã nộp, Đang kiểm tra ban đầu, Đang thẩm định, Đang xem xét
        kết quả:</strong> bộ phận xử lý đang làm việc; theo dõi, chưa gửi lại.</li>
        <li><strong>Cần bổ sung:</strong> mở yêu cầu, sửa đúng nội dung và gửi lại.</li>
        <li><strong>Đã phê duyệt:</strong> chờ bước phí hoặc phát hành tùy hồ sơ;
        chỉ thanh toán khi có yêu cầu phí hiển thị.</li>
        <li><strong>Chờ thanh toán:</strong> kiểm tra khoản phí, mở lần thanh
        toán đang có và theo dõi xác nhận.</li>
        <li><strong>Đã thanh toán, Đang chuẩn bị bằng xác lập, Sẵn sàng phát
        hành:</strong> theo dõi, không trả thêm phí cho cùng yêu cầu.</li>
        <li><strong>Đã phát hành bằng xác lập, Đã công bố:</strong> xem bằng
        trong tài khoản; công bố là giai đoạn riêng.</li>
        <li><strong>Bị từ chối, Đã hủy, Đã thu hồi:</strong> xem lý do và lịch
        sử; không mặc định có nút sửa hoặc gửi lại.</li></ul>
        <h2>Khi có yêu cầu bổ sung</h2><ol><li>Đọc nội dung cần bổ sung ở
        trang chi tiết và xác định tệp/trường liên quan.</li><li>Sửa phần được
        mở, kiểm tra thông báo lưu và tài liệu mới.</li><li>Gửi lại, sau đó
        kiểm tra phiên bản và trạng thái mới trong lịch sử.</li></ol>
        <h2>Nếu trạng thái chưa thay đổi</h2><p>Tải lại trang và xem lịch sử.
        Nếu đã nộp hoặc thanh toán nhưng kết quả chưa cập nhật, giữ mã hồ sơ
        và mã giao dịch để liên hệ hỗ trợ; đừng lặp thao tác thanh toán.</p>
        """,
    ),
    (
        "dossier-payment-guide",
        "Thanh toán phí hồ sơ theo yêu cầu",
        "Phân biệt yêu cầu phí, lần thanh toán và trạng thái được xác nhận.",
        "dossiers",
        ("USER",),
        35,
        """
        <h2>Khi nào cần thanh toán?</h2><p>Hồ sơ đã được phê duyệt chưa tự
        phát sinh khoản phải trả. Quản trị viên phát hành yêu cầu phí hoặc
        ghi nhận miễn phí theo trường hợp. Chỉ khi trang chi tiết hồ sơ báo
        <strong>Chờ thanh toán</strong> và hiện khoản phí, bạn mới thực hiện
        thanh toán. Hiện không có bước nạp tiền vào số dư tài khoản.</p>
        <h2>Các bước</h2><ol>
        <li>Mở đúng hồ sơ trong <a href="/dossiers">Hồ sơ của tôi</a>. Đọc
        số tiền và nội dung yêu cầu, đối chiếu mã hồ sơ.</li>
        <li>Nếu đã có lần thanh toán đang hoạt động, mở lần đó. Nếu màn hình
        cho phép, chọn <strong>Thanh toán trực tuyến</strong> để mở trang thanh
        toán cho yêu cầu phí hiện tại. Người nộp không tự nhập số tiền.</li>
        <li>Trên trang lần thanh toán, đối chiếu số tiền, thời hạn, mã tham
        chiếu và cách trả tiền đang hiển thị; hoàn tất theo chỉ dẫn trên trang.</li>
        <li>Quay lại trang thanh toán, chọn <strong>Kiểm tra trạng thái ngay</strong>
        nếu cần; mở lại hồ sơ để xem trạng thái. Chỉ coi là xong khi màn hình
        báo thanh toán được xác nhận.</li></ol>
        <h2>Hủy và lỗi</h2><p>Nút Hủy lần thanh toán chỉ áp dụng khi lần đó
        còn được hủy; hủy lần thanh toán không hủy hồ sơ. Nếu đã trả tiền
        nhưng trang chưa cập nhật, kiểm tra lại trạng thái bằng mã tham chiếu,
        không mở thêm lần thanh toán ngay. Giữ thông tin giao dịch và liên hệ
        hỗ trợ khi vẫn chưa được xác nhận.</p>
        <h2>Sau khi xác nhận</h2><p>Hồ sơ chuyển sang Đã thanh toán rồi tiếp
        tục các bước chuẩn bị và phát hành bằng. Xem dòng thời gian hồ sơ;
        thanh toán thành công chưa phải kết quả phát hành cuối cùng.</p>
        """,
    ),
    (
        "dossier-faq",
        "Câu hỏi thường gặp khi nộp hồ sơ",
        "Giải đáp lỗi gửi, chỉnh sửa, bổ sung, thanh toán và xem kết quả.",
        "dossiers",
        ("USER",),
        36,
        """
        <h2>Câu hỏi thường gặp</h2>
        <h3>Vì sao tôi không gửi được hồ sơ?</h3><p>Kiểm tra trường và tài
        liệu bắt buộc, trạng thái lưu và quyền chỉnh sửa. Chỉ bản nháp hoặc
        hồ sơ được yêu cầu bổ sung mới có luồng gửi phù hợp.</p>
        <h3>Hồ sơ đã nộp có sửa được không?</h3><p>Trang chi tiết khóa sửa khi
        hồ sơ đang được xử lý. Nếu chuyển sang Cần bổ sung, đọc yêu cầu rồi
        sửa và gửi lại trên chính hồ sơ đó.</p>
        <h3>Tôi biết ai đang xử lý ở đâu?</h3><p>Xem nhãn và dòng thời gian
        trong chi tiết hồ sơ. Trang có thể hiển thị giai đoạn xử lý, nhưng
        không hứa công khai danh tính mọi người tham gia.</p>
        <h3>Nếu bị yêu cầu bổ sung?</h3><p>Đọc nội dung yêu cầu tại hồ sơ,
        sửa phần liên quan, đợi lưu và gửi lại. Kiểm tra phiên bản mới.</p>
        <h3>Tôi có thể rút hồ sơ không?</h3><p>Không có thao tác rút hồ sơ tự
        phục vụ trong trang hồ sơ hiện tại. Nếu cần dừng xử lý, liên hệ hỗ trợ
        và cung cấp mã hồ sơ.</p>
        <h3>Xem kết quả ở đâu?</h3><p>Xem trạng thái hồ sơ; nếu đã phát hành,
        mở <a href="/certificates">Bằng xác lập</a>.</p>
        <h3>Khi nào cần trả phí?</h3><p>Chỉ khi có yêu cầu phí và hồ sơ hiện
        Chờ thanh toán. Phê duyệt tự nó chưa tạo giao dịch.</p>
        <h3>Đã trả nhưng trạng thái chưa đổi?</h3><p>Mở lần thanh toán hiện có,
        kiểm tra trạng thái. Giữ mã tham chiếu, không thanh toán lại khi kết quả
        trước chưa được xác minh.</p>
        """,
    ),
    (
        "review-process-and-scorecard",
        "Thẩm định hồ sơ và chấm phiếu 5 tiêu chí",
        "Từ nhận phân công đến kiểm tra minh chứng, lưu nháp và gửi đề xuất.",
        "review-workflows",
        ("MODERATOR",),
        52,
        """
        <h2>Điều kiện bắt đầu</h2><p>Bạn cần được phân công đúng phiên bản
        hồ sơ đang thẩm định. Mở <a href="/reviews">Thẩm định của tôi</a>
        hoặc <a href="/work-allocations">Công việc được giao</a> để chọn việc.
        Không xử lý hồ sơ ngoài phạm vi phân công.</p>
        <h2>Quy trình</h2><ol>
        <li>Kiểm tra mã hồ sơ, phiên bản, hạn và trạng thái phân công. Mở
        chi tiết để đọc thông tin, tài liệu và minh chứng được cấp quyền xem.</li>
        <li>Nếu có xung đột lợi ích, khai báo trong trang phân công và chờ
        quản trị viên xử lý; không gửi đánh giá cho hồ sơ đó.</li>
        <li>Hoàn thành phiếu theo 5 nhóm: Tính đúng đắn, Tính minh bạch,
        Quyền sở hữu và trách nhiệm, Tính chuyên nghiệp, Tính tôn trọng.
        Mỗi nhóm chấm từ 0 đến 20 theo thang hiển thị trên phiếu và ghi nhận
        nhận xét dựa trên minh chứng.</li>
        <li>Kiểm tra các mục xác nhận, phát hiện cần xử lý và chọn đề xuất:
        phê duyệt, yêu cầu bổ sung hoặc từ chối. Nếu đề xuất bổ sung hoặc từ
        chối, nhập phản hồi cho người nộp; đề xuất bổ sung cần có phát hiện
        tương ứng.</li>
        <li>Kiểm tra trạng thái lưu nháp. Chọn <strong>Gửi kết quả thẩm định</strong>,
        đọc xác nhận rồi chọn <strong>Xác nhận gửi</strong>.</li></ol>
        <h2>Kết quả</h2><p>Phân công chuyển sang đã gửi; quản trị viên xem
        kết quả để quyết định bước tiếp theo. Điểm và đề xuất của một người
        thẩm định không tự phê duyệt hoặc công bố hồ sơ.</p>
        <h2>Nếu chưa gửi được</h2><p>Kiểm tra đủ 5 điểm, nhận xét và các mục
        xác nhận; xem cảnh báo lưu nháp. Nếu phân công đã hủy hoặc hồ sơ đổi
        phiên bản, liên hệ người phân công. Không dựa vào điểm đã nhập nếu
        trang báo lưu thất bại.</p>
        """,
    ),
    (
        "review-exceptions-faq",
        "Tình huống đặc biệt khi thẩm định",
        "Xử lý xung đột, thiếu minh chứng, lỗi lưu và kết quả đã gửi.",
        "review-workflows",
        ("MODERATOR",),
        53,
        """
        <h2>Câu hỏi thường gặp</h2>
        <h3>Vì sao tôi không thấy hồ sơ?</h3><p>Kiểm tra hàng đợi và tài
        khoản đang dùng. Quản trị viên chỉ định người và phiên bản hồ sơ;
        hỏi người phân công nếu việc chưa xuất hiện.</p>
        <h3>Thiếu tài liệu thì làm gì?</h3><p>Ghi nhận phần thiếu trong phát
        hiện và nhận xét. Nếu đủ điều kiện, chọn đề xuất yêu cầu bổ sung và
        viết phản hồi rõ phần cần làm; không tự sửa hồ sơ của người nộp.</p>
        <h3>Có thể để phiếu chưa xong không?</h3><p>Phiếu hỗ trợ lưu nháp tự
        động. Kiểm tra trạng thái lưu trước khi rời trang; cảnh báo lỗi lưu
        nghĩa là thay đổi chưa được ghi nhận.</p>
        <h3>Vì sao nút gửi bị khóa?</h3><p>Có thể thiếu điểm, nhận xét, mục
        xác nhận, phản hồi bắt buộc hoặc phát hiện đi kèm đề xuất bổ sung.
        Xem thông báo cụ thể trên phiếu rồi hoàn thiện.</p>
        <h3>Có sửa sau khi gửi không?</h3><p>Phiếu đã gửi là kết quả của lần
        phân công đó; không có thao tác tự sửa kết quả đã chốt. Liên hệ quản
        trị viên khi phát hiện sai sót hoặc cần đánh giá lại.</p>
        <h3>Nếu có xung đột hoặc việc bị hủy?</h3><p>Dừng xử lý và báo trong
        luồng phân công. Chỉ tiếp tục khi có phân công hợp lệ.</p>
        """,
    ),
    (
        "admin-attendance-configuration",
        "Tạo, phân công và theo dõi điểm chấm công",
        "Thiết lập địa điểm, chính sách vùng, lịch hiệu lực và kiểm tra ngoại lệ.",
        "administration",
        ("SUPER_ADMIN",),
        85,
        """
        <h2>Điều kiện</h2><p>Nhân viên cần có hồ sơ liên kết tài khoản.
        Điểm chấm công, chính sách vùng và phân công phải có hiệu lực trong
        ngày làm việc thì nhân viên mới dùng được.</p>
        <h2>Thiết lập</h2><ol>
        <li>Mở <a href="/admin/attendance/worksites">Điểm chấm công</a>.
        Chọn Thêm địa điểm, nhập mã, tên và địa chỉ. Đặt vị trí trên bản đồ,
        kiểm tra tọa độ rồi lưu.</li>
        <li>Chọn địa điểm, tạo chính sách vùng với bán kính, độ sai lệch
        cho phép và thời điểm hiệu lực. Kiểm tra bản đồ trước khi lưu.</li>
        <li>Trong phần phân công, tìm đúng nhân viên và gắn điểm làm việc
        theo thời gian áp dụng. Đối chiếu ngày bắt đầu/kết thúc với lịch của
        nhân viên; kiểm tra danh sách phân công sau khi lưu.</li>
        <li>Mở <a href="/admin/attendance">Chấm công</a> để xem bản ghi,
        giờ vào/ra và trường hợp cần xem xét.</li></ol>
        <h2>Thay đổi hoặc ngừng dùng</h2><p>Địa điểm có thể chuyển hoạt động
        hoặc ngừng hoạt động. Khi vị trí/chính sách cũ sai, dùng chức năng
        điều chỉnh có lý do và hiệu lực phù hợp; kiểm tra lịch sử thay vì
        cho rằng bản ghi chấm công cũ đã tự thay đổi.</p>
        <h2>Nếu nhân viên không chấm được</h2><p>Kiểm tra liên kết tài khoản,
        lịch, phân công điểm, trạng thái hoạt động, chính sách vùng và quyền
        vị trí trên thiết bị. Đọc lý do ngoại lệ trước khi điều chỉnh.</p>
        """,
    ),
    (
        "admin-allocation-process",
        "Tạo và theo dõi phân công công việc",
        "Phân biệt giao hồ sơ thẩm định với đầu việc chung, theo dõi người thực hiện.",
        "administration",
        ("SUPER_ADMIN",),
        86,
        """
        <h2>Chọn đúng loại việc</h2><p>Mở
        <a href="/admin/work-allocations">Phân công công việc</a>. Trang có
        hai luồng: giao hồ sơ để thẩm định và tạo đầu việc chung. Phiếu thẩm
        định là nơi gửi kết luận chuyên môn; nút hoàn thành phần việc chỉ dùng
        cho đầu việc chung.</p>
        <h2>Giao hồ sơ thẩm định</h2><ol>
        <li>Chọn Giao hồ sơ thẩm định, mở đúng hồ sơ và kiểm tra trạng thái,
        phiên bản, tài liệu cần người thẩm định xem.</li>
        <li>Chọn người thực hiện và phạm vi minh chứng nếu biểu mẫu yêu cầu;
        kiểm tra hạn, trách nhiệm rồi chọn Giao hồ sơ để thẩm định.</li>
        <li>Kiểm tra dòng phân công; người được giao mở hồ sơ trong hàng đợi
        của họ. Theo dõi kết quả thẩm định ở khu vực tiếp nhận hồ sơ.</li></ol>
        <h2>Giao đầu việc chung</h2><ol>
        <li>Chọn Giao công việc. Nhập Mục tiêu công việc, Mô tả nếu cần,
        Hạn hoàn thành và Mức độ ưu tiên.</li>
        <li>Chọn ít nhất một Người cùng thực hiện và kiểm tra Người phụ trách chính;
        kiểm tra danh sách người trước khi xác nhận.</li>
        <li>Xem phân công trong danh sách; theo dõi tiến độ của từng người.
        Người được giao đánh dấu Hoàn thành phần việc trên trang của họ;
        kiểm tra trạng thái toàn việc sau khi các phần việc xong.</li></ol>
        <h2>Khi cần điều chỉnh</h2><p>Kiểm tra trạng thái trước khi hủy phân
        công. Nếu trang không có thao tác sửa trực tiếp cho trường cần đổi,
        không giả định có thể sửa một việc đang chạy; đối chiếu lịch sử, hủy
        nếu được phép rồi tạo phân công đúng. Việc hủy không xóa kết quả thẩm
        định đã gửi.</p>
        <h2>Nếu người nhận không thấy việc</h2><p>Kiểm tra đúng tài khoản,
        người được chọn, trạng thái phân công và bộ lọc của họ.</p>
        """,
    ),
    (
        "admin-dossier-decision-process",
        "Tiếp nhận thẩm định và quyết định hồ sơ",
        "Đọc báo cáo kiểm duyệt, yêu cầu bổ sung, phê duyệt hoặc từ chối "
        "đúng giai đoạn.",
        "administration",
        ("SUPER_ADMIN",),
        87,
        """
        <h2>Điểm bắt đầu</h2><p>Mở
        <a href="/admin/reviews">Tiếp nhận hồ sơ</a> và chọn hồ sơ đã nộp.
        Kiểm tra mã, phiên bản và trạng thái trước khi thực hiện kiểm tra ban
        đầu hoặc giao thẩm định.</p>
        <h2>Từ phân công đến báo cáo</h2><ol>
        <li>Kiểm tra hồ sơ và minh chứng; giao đúng người thẩm định trong
        <a href="/admin/work-allocations">Phân công công việc</a>. Đối chiếu
        phiên bản hồ sơ và người được giao.</li>
        <li>Theo dõi các phân công. Mở báo cáo kiểm duyệt, xem điểm, nhận
        xét, phát hiện, đề xuất và minh chứng tương ứng của từng người.</li>
        <li>Chờ mọi phân công hoàn tất. Khu vực Quyết định cuối sẽ báo khi
        chưa đủ kết quả; không ra quyết định dựa trên báo cáo còn dở dang.</li>
        </ol><h2>Ra quyết định</h2><ol>
        <li>Nhập Lý do quyết định cuối, nêu căn cứ từ báo cáo và tài liệu.
        Kiểm tra nội dung trước khi chọn hành động.</li>
        <li>Chọn <strong>Yêu cầu bổ sung</strong> nếu cần người nộp cung cấp
        thêm; hồ sơ sẽ mở luồng bổ sung cho họ.</li>
        <li>Với <strong>Phê duyệt hồ sơ</strong> hoặc <strong>Từ chối hồ sơ</strong>,
        xác nhận đã đọc báo cáo và không có xung đột lợi ích rồi chọn đúng
        quyết định. Đọc kết quả trên trang sau khi gửi.</li></ol>
        <h2>Sau quyết định</h2><p>Hồ sơ đã phê duyệt có thể được đưa tới
        bước quyết định phí; hồ sơ bị từ chối dừng tại kết quả đó. Yêu cầu bổ
        sung đưa việc trở lại người nộp, sau khi họ gửi lại cần kiểm tra phiên
        bản mới. Nếu thao tác lỗi, kiểm tra trạng thái hiện tại trước khi bấm
        lại để tránh ghi nhận hai lần.</p>
        """,
    ),
    (
        "admin-fee-decision-process",
        "Quyết định thu hoặc miễn phí hồ sơ",
        "Chọn hồ sơ đã duyệt, ghi khoản phí hoặc lý do miễn, rồi đối chiếu trạng thái.",
        "administration",
        ("SUPER_ADMIN",),
        88,
        """
        <h2>Điều kiện</h2><p>Mở <a href="/admin/payments">Thu phí</a>.
        Danh sách chọn chỉ gồm hồ sơ đã phê duyệt đang chờ quyết định phí.
        Không tự tạo yêu cầu cho hồ sơ còn thẩm định hoặc đã có quyết định phí.</p>
        <h2>Có thu phí</h2><ol><li>Chọn đúng hồ sơ theo mã và tên, chọn
        <strong>Có thu phí</strong>.</li><li>Nhập Số tiền cần thanh toán,
        Nội dung khoản phí và Hạn thanh toán nếu có. Đối chiếu số tiền theo
        căn cứ áp dụng và kiểm tra lại mã hồ sơ.</li><li>Chọn
        <strong>Gửi yêu cầu thanh toán</strong>, kiểm tra thông báo và trạng
        thái mới của hồ sơ. Người nộp sẽ thấy khoản phí ở trang hồ sơ và có
        thể mở lần thanh toán.</li></ol>
        <h2>Miễn phí</h2><ol><li>Chọn hồ sơ, chọn <strong>Miễn phí</strong>.
        Nhập Lý do miễn phí rõ căn cứ.</li><li>Chọn <strong>Xác nhận miễn
        phí</strong>, kiểm tra kết quả. Hồ sơ bỏ qua thao tác trả tiền và
        chuyển tới bước xử lý phát hành.</li></ol>
        <h2>Khi giao dịch chưa khớp</h2><p>Đối chiếu mã hồ sơ, yêu cầu phí
        và lần thanh toán đang có. Nếu người nộp báo đã trả nhưng chưa được
        xác nhận, kiểm tra trạng thái và mã tham chiếu trước khi xử lý; không
        phát hành khoản thu trùng. Nếu quyết định phí gửi lỗi, tải lại trạng
        thái hồ sơ trước khi thử lại.</p>
        """,
    ),
    (
        "admin-reviewer-invitations",
        "Mời và quản lý người kiểm duyệt",
        "Chọn tài khoản đủ điều kiện, gửi lời mời và theo dõi quyền truy cập.",
        "administration",
        ("SUPER_ADMIN",),
        89,
        """
        <h2>Điều kiện</h2><p>Mở <a href="/admin/staff">Nhân sự phụ trách</a>.
        Người được mời phải có tài khoản đang hoạt động và đã xác minh email.
        Lời mời không tự cấp quyền ngay; người nhận phải chấp nhận.</p>
        <h2>Mời người kiểm duyệt</h2><ol>
        <li>Trong Chọn người kiểm duyệt, tìm tài khoản theo tên hoặc email.
        Đối chiếu đúng người và chọn Chọn làm người kiểm duyệt.</li>
        <li>Đọc hộp xác nhận, kiểm tra email và nhiệm vụ rồi chọn Gửi lời mời.
        Người nhận xem thông báo và tự chấp nhận để bắt đầu được phân công.</li>
        <li>Xem Lời mời gần đây: Chờ xác nhận, Đã kích hoạt, Đã thu hồi hoặc
        Đã hết hạn. Lời mời chờ xác nhận có thể Gửi lại hoặc Thu hồi.</li></ol>
        <h2>Quản lý tài khoản phụ trách</h2><p>Tìm đúng email trong danh
        sách. Khi mở hồ sơ nhân viên, khóa, mở khóa hoặc vô hiệu hóa, đọc hộp
        xác nhận trước khi quyết định. Khóa hoặc vô hiệu hóa sẽ kết thúc các
        phiên truy cập; lịch sử công việc vẫn được bảo toàn.</p>
        <h2>Nếu không có tài khoản để chọn</h2><p>Kiểm tra tài khoản đã hoạt
        động và xác minh email. Nếu lời mời hết hạn, kiểm tra trạng thái trước
        khi gửi lại; không giao hồ sơ cho người chưa nhận quyền.</p>
        """,
    ),
    (
        "admin-attendance-corrections",
        "Xem ngoại lệ và điều chỉnh chấm công",
        "Lọc bản ghi, xét duyệt vị trí và sửa số liệu với lý do rõ ràng.",
        "administration",
        ("SUPER_ADMIN",),
        90,
        """
        <h2>Điểm bắt đầu</h2><p>Mở
        <a href="/admin/attendance">Chấm công</a>. Tìm nhân viên, chọn
        khoảng ngày và trạng thái để thu hẹp danh sách.</p>
        <h2>Xử lý từng bản ghi</h2><ol>
        <li>Mở đúng nhân viên và ngày làm việc. Đối chiếu giờ vào, giờ ra,
        vị trí và trạng thái với điểm/lịch đã phân công.</li>
        <li>Nếu là trường hợp cần xét duyệt vị trí, dùng phần xét duyệt vị
        trí để đọc minh chứng rồi ra quyết định tại đó. Không đổi trạng thái
        vị trí bằng biểu mẫu Điều chỉnh.</li>
        <li>Với sai lệch giờ hoặc số phút đi muộn/về sớm, chọn Điều chỉnh.
        Nhập giờ vào, giờ ra, trạng thái được phép, số phút và Ghi chú nội
        bộ theo căn cứ đã kiểm tra.</li>
        <li>Đọc hộp xác nhận và lưu. Mở lại bản ghi để đối chiếu số liệu và
        trạng thái sau điều chỉnh.</li></ol>
        <h2>Nếu chưa thể điều chỉnh</h2><p>Kiểm tra trạng thái hiện tại và
        thông báo lỗi. Trạng thái xét duyệt vị trí phải xử lý trong phần
        riêng. Nếu dữ liệu vừa thay đổi bởi người khác, tải lại bản ghi trước
        khi quyết định lần nữa.</p>
        """,
    ),
)


def upgrade() -> None:
    now = datetime.now(UTC)
    table = sa.table(
        "cms_guide_articles",
        sa.column("id", sa.Uuid()),
        sa.column("title", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("summary", sa.String()),
        sa.column("category", sa.String()),
        sa.column("audiences", sa.JSON()),
        sa.column("body_html", sa.Text()),
        sa.column("search_text", sa.Text()),
        sa.column("search_title", sa.Text()),
        sa.column("search_summary", sa.Text()),
        sa.column("sort_order", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_by", sa.Uuid()),
        sa.column("updated_by", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": UUID(f"11111111-1111-4111-8111-{400 + index:012d}"),
                "slug": slug,
                "title": title,
                "summary": summary,
                "category": category,
                "audiences": list(audiences),
                "body_html": body,
                "search_text": _search(f"{title} {summary} {category} {body}"),
                "search_title": _search(title),
                "search_summary": _search(summary),
                "sort_order": order,
                "status": "PUBLISHED",
                "version": 1,
                "published_at": now,
                "created_by": None,
                "updated_by": None,
                "created_at": now,
                "updated_at": now,
            }
            for index, (
                slug,
                title,
                summary,
                category,
                audiences,
                order,
                body,
            ) in enumerate(_GUIDES)
        ],
    )


def downgrade() -> None:
    slugs = [guide[0] for guide in _GUIDES]
    op.execute(
        sa.text(
            "DELETE FROM cms_guide_articles WHERE slug IN "
            f"({', '.join(f':slug_{index}' for index in range(len(slugs)))}) "
            "AND created_by IS NULL AND updated_by IS NULL AND version = 1"
        ).bindparams(**{f"slug_{index}": slug for index, slug in enumerate(slugs)})
    )
