"""Add focused guides for verified role workflows.

Revision ID: 0116_role_workflow_guides
Revises: 0115_public_guide_plain_language
"""

import re
import unicodedata
from collections.abc import Sequence
from datetime import UTC, datetime
from html import unescape
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0116_role_workflow_guides"
down_revision: str | None = "0115_public_guide_plain_language"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _search(value: str) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    decomposed = unicodedata.normalize("NFKD", plain)
    unmarked = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unmarked.replace("đ", "d").replace("Đ", "d").casefold().split())


# Each article describes a route and controls checked against the current UI.
_GUIDES = (
    (
        "moderator-work-allocations",
        "Theo dõi công việc được giao",
        "Xem hồ sơ thẩm định và đánh dấu phần việc chung đã hoàn thành.",
        "review-workflows",
        ("MODERATOR",),
        51,
        """
        <h2>Khi nào dùng?</h2><p>Mở danh sách khi bạn được giao hồ sơ thẩm định
        hoặc một đầu việc chung. Chỉ công việc giao cho tài khoản của bạn mới
        xuất hiện.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/work-allocations">Công việc được giao</a>. Kiểm tra
        mục Hồ sơ thẩm định được giao và Đầu việc khác.</li>
        <li>Với hồ sơ thẩm định, đối chiếu tên, mã, hạn xử lý và trạng thái;
        chọn Bắt đầu thẩm định hoặc Tiếp tục thẩm định để mở phiếu. Kết luận
        thẩm định được gửi trong phiếu, không gửi từ danh sách công việc.</li>
        <li>Với đầu việc chung, đọc mục tiêu, mô tả, mức ưu tiên và hạn.
        Chỉ chọn Hoàn thành phần việc sau khi việc của bạn thực sự xong.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Đầu việc chung hiện thông báo Bạn đã hoàn
        thành phần việc này. Nếu là hồ sơ thẩm định, quay lại hàng đợi để
        kiểm tra trạng thái phiếu sau khi gửi kết quả.</p>
        <h2>Nếu không thấy việc</h2><p>Kiểm tra bộ lọc và tài khoản đang dùng.
        Nếu vẫn trống, liên hệ người phân công để đối chiếu.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/review-an-assigned-dossier">Xử lý hồ sơ được phân công</a>.</p>
        """,
    ),
    (
        "employee-attendance",
        "Chấm công vào và ra",
        "Ghi nhận giờ làm tại điểm được phân công và kiểm tra lịch sử.",
        "employee-workflows",
        ("EMPLOYEE",),
        61,
        """
        <h2>Điều kiện sử dụng</h2><p>Tài khoản cần liên kết hồ sơ nhân viên,
        có ngày làm việc và điểm chấm công đang áp dụng. Thiết bị cần cho phép
        trang web dùng vị trí.</p>
        <h2>Cách chấm công</h2><ol>
        <li>Đến điểm làm việc được phân công rồi mở
        <a href="/attendance">Chấm công</a>.</li>
        <li>Kiểm tra ngày làm việc và điểm được hiển thị. Chọn Chấm công vào
        khi bắt đầu ca; cho phép truy cập vị trí nếu trình duyệt hỏi.</li>
        <li>Cuối ca, chọn Chấm công ra. Xem giờ vào, giờ ra và trạng thái
        trong lịch sử chấm công.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Trang báo đã ghi nhận giờ vào hoặc giờ ra.
        Nếu hiện thiếu giờ hoặc cần xem xét, mở dòng ngày làm việc và kiểm tra
        thông tin vị trí trước khi liên hệ quản trị viên.</p>
        <h2>Khi không thể chấm công</h2><p>Nếu nút báo Chưa thể chấm công vào,
        liên hệ quản trị viên để kiểm tra lịch và điểm làm việc. Nếu không lấy
        được vị trí, kiểm tra quyền vị trí của thiết bị và thử lại tại điểm
        được phân công.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/employee-leave-request">Gửi đơn nghỉ</a>.</p>
        """,
    ),
    (
        "employee-leave-request",
        "Gửi và theo dõi đơn nghỉ",
        "Điền loại nghỉ, khoảng ngày, lý do và xem kết quả duyệt.",
        "employee-workflows",
        ("EMPLOYEE",),
        62,
        """
        <h2>Điều kiện sử dụng</h2><p>Tài khoản cần liên kết hồ sơ nhân viên.
        Chuẩn bị ngày bắt đầu, ngày kết thúc và lý do để người duyệt xem xét.</p>
        <h2>Cách gửi đơn</h2><ol>
        <li>Mở <a href="/leave">Nghỉ phép</a>, tìm phần Đơn nghỉ mới.</li>
        <li>Nhập Loại nghỉ, Từ ngày, Đến ngày và Lý do. Kiểm tra khoảng ngày
        trước khi gửi.</li>
        <li>Chọn Gửi đơn nghỉ. Xem đơn trong danh sách bên dưới và theo dõi
        trạng thái duyệt tại đây.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Đơn mới xuất hiện trong danh sách yêu cầu.
        Việc gửi đơn chưa đồng nghĩa với được chấp thuận.</p>
        <h2>Nếu gửi không thành công</h2><p>Đọc thông báo ngay dưới biểu mẫu,
        kiểm tra các trường bắt buộc và khoảng ngày rồi thử lại. Nếu không thấy
        mục Nghỉ phép, liên hệ quản trị viên kiểm tra liên kết hồ sơ nhân viên.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/employee-overtime-request">Đăng ký tăng ca</a>.</p>
        """,
    ),
    (
        "employee-overtime-request",
        "Đăng ký và theo dõi tăng ca",
        "Gửi thời gian dự kiến, lý do và kiểm tra kết quả duyệt.",
        "employee-workflows",
        ("EMPLOYEE",),
        63,
        """
        <h2>Điều kiện sử dụng</h2><p>Tài khoản cần liên kết hồ sơ nhân viên.
        Xác định giờ bắt đầu, giờ kết thúc và lý do tăng ca trước khi gửi.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/overtime">Tăng ca</a> và tìm phần Thời gian dự kiến.</li>
        <li>Nhập Bắt đầu, Kết thúc và Lý do tăng ca. Kiểm tra đúng ngày,
        giờ trên thiết bị và bảo đảm giờ kết thúc sau giờ bắt đầu.</li>
        <li>Chọn Gửi yêu cầu tăng ca rồi kiểm tra yêu cầu trong danh sách.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Yêu cầu hiện trong lịch sử để theo dõi
        trạng thái. Việc gửi yêu cầu chưa phải là phê duyệt hoặc xác nhận
        khoản chi trả.</p>
        <h2>Nếu bị từ chối hoặc gửi lỗi</h2><p>Xem trạng thái và thông báo
        trên trang. Kiểm tra lại khoảng thời gian và lý do; liên hệ người
        duyệt nếu cần làm rõ quyết định.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/employee-attendance">Chấm công vào và ra</a>.</p>
        """,
    ),
    (
        "admin-review-assignments",
        "Phân công và theo dõi thẩm định",
        "Giao hồ sơ cho người thẩm định và đối chiếu kết quả trước khi quyết định.",
        "administration",
        ("SUPER_ADMIN",),
        81,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi hồ sơ đã vào hàng đợi thẩm định
        và cần giao người xử lý. Người thẩm định chỉ xem hồ sơ được phân công.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/reviews">Tiếp nhận hồ sơ</a>, chọn hồ sơ cần
        xử lý và kiểm tra mã, trạng thái, phiên bản tài liệu.</li>
        <li>Chọn người thẩm định phù hợp và xác nhận phân công. Theo dõi hạn
        xử lý và tiến độ trong hàng đợi.</li>
        <li>Khi nhận kết quả, đối chiếu nhận xét với đúng phiên bản hồ sơ,
        lý do bổ sung hoặc từ chối trước khi quyết định bước tiếp theo.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Hồ sơ hiện người được giao; người đó thấy
        hồ sơ trong hàng đợi cá nhân. Kết quả thẩm định không tự công bố hồ sơ.</p>
        <h2>Nếu người thẩm định không thấy hồ sơ</h2><p>Kiểm tra tài khoản,
        trạng thái phân công và mã hồ sơ trước khi giao lại.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/admin-payment-requests">Tạo yêu cầu thanh toán</a>
        sau khi hồ sơ đến đúng giai đoạn.</p>
        """,
    ),
    (
        "admin-payment-requests",
        "Tạo và đối chiếu yêu cầu thanh toán",
        "Tạo khoản phí đúng hồ sơ, kiểm tra số tiền và xử lý giao dịch chưa cập nhật.",
        "administration",
        ("SUPER_ADMIN",),
        82,
        """
        <h2>Khi nào dùng?</h2><p>Chỉ tạo yêu cầu khi hồ sơ đã tới giai đoạn
        được phép thu phí và mức phí đã được xác nhận.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/payments">Thu phí</a>, chọn đúng hồ sơ theo
        mã và kiểm tra trạng thái hiện tại.</li>
        <li>Nhập số tiền theo biểu phí áp dụng, nội dung khoản phí và hạn
        thanh toán. Đối chiếu lại trước khi gửi.</li>
        <li>Gửi yêu cầu rồi theo dõi trạng thái thanh toán trên hồ sơ.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Yêu cầu thanh toán xuất hiện ở đúng hồ sơ
        với số tiền và hạn đã kiểm tra.</p>
        <h2>Nếu người nộp đã trả nhưng trạng thái chưa đổi</h2><p>Đối chiếu
        mã hồ sơ và mã giao dịch trước khi xử lý. Không tạo khoản thu thứ hai
        khi giao dịch đầu chưa được xác minh.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/admin-review-assignments">Phân công thẩm định</a>.</p>
        """,
    ),
    (
        "admin-guide-publishing",
        "Soạn và xuất bản bài hướng dẫn",
        "Tạo bản nháp, kiểm tra phạm vi người đọc và xuất bản bài viết.",
        "administration",
        ("SUPER_ADMIN",),
        83,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi cần thêm hoặc sửa hướng dẫn cho
        một quy trình đã được triển khai.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/guide/articles">Quản lý bài viết hướng dẫn</a>.
        Tìm bài hiện có trước khi tạo bài mới để tránh trùng nội dung.</li>
        <li>Nhập tiêu đề, tóm tắt, chủ đề và nội dung từng bước. Chọn đúng
        nhóm người đọc theo chức năng họ được sử dụng.</li>
        <li>Lưu bản nháp, xem trước nội dung và thử các liên kết. Khi đã
        kiểm tra xong, chọn xuất bản.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Bài đã xuất bản xuất hiện trong trang
        Hướng dẫn của nhóm người đọc được chọn. Bài chỉ hiện công khai nếu
        được chọn phạm vi Mọi người.</p>
        <h2>Khi cần ngừng hiển thị</h2><p>Chuyển bài sang lưu trữ trong
        trang quản lý rồi kiểm tra lại danh sách hướng dẫn.</p>
        """,
    ),
    (
        "admin-worksite-attendance",
        "Thiết lập điểm chấm công",
        "Tạo điểm làm việc, kiểm tra vùng cho phép và theo dõi ngoại lệ.",
        "administration",
        ("SUPER_ADMIN",),
        84,
        """
        <h2>Khi nào dùng?</h2><p>Thiết lập điểm làm việc trước khi phân công
        lịch chấm công cho nhân viên.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/attendance/worksites">Điểm chấm công</a>.
        Chọn địa điểm hiện có để kiểm tra hoặc chọn Thêm địa điểm, nhập mã
        và tên dễ nhận biết.</li>
        <li>Đặt địa chỉ và tâm vùng trên bản đồ; kiểm tra vĩ độ, kinh độ,
        bán kính, độ sai lệch cho phép và ngày hiệu lực trước khi lưu.</li>
        <li>Liên kết hồ sơ nhân viên với tài khoản và phân công lịch, điểm
        làm việc. Sau đó mở <a href="/admin/attendance">Chấm công</a>
        để theo dõi giờ vào, giờ ra và trường hợp cần xem xét.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Điểm hiển thị đúng vị trí trên bản đồ,
        chính sách đã có hiệu lực và nhân viên thấy lịch tương ứng.</p>
        <h2>Khi vị trí đã lưu sai</h2><p>Chọn Sửa vị trí đã lưu, nhập vị trí
        đúng và lý do điều chỉnh. Kiểm tra lại bản đồ và lịch sử thay đổi.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/admin-employee-payroll">Quản lý nhân viên và bảng lương</a>.</p>
        """,
    ),
    (
        "admin-employee-payroll",
        "Quản lý nhân viên và bảng lương",
        "Liên kết tài khoản nhân viên và đối chiếu kỳ lương trước khi xác nhận.",
        "administration",
        ("SUPER_ADMIN",),
        85,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi tiếp nhận nhân viên hoặc lập
        bảng lương cho một kỳ đã có dữ liệu chấm công và yêu cầu nhân sự.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/employees">Nhân sự</a>, tìm tài khoản bằng
        email. Nếu chưa có, gửi lời mời và chờ xác minh địa chỉ.</li>
        <li>Tạo hoặc mở hồ sơ nhân viên, liên kết đúng tài khoản rồi nhập
        phòng ban, vị trí, hợp đồng và thông tin lương được phép quản lý.</li>
        <li>Mở <a href="/admin/payroll">Bảng lương</a>, chọn kỳ cần xử lý.
        Đối chiếu ngày công, nghỉ phép, tăng ca và khoản điều chỉnh
        trước khi xác nhận số liệu.</li>
        <li>Chỉ chọn Đánh dấu đã chi sau khi đã xác nhận việc chuyển tiền
        ngoài hệ thống; tải báo cáo để đối chiếu chứng từ.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Hồ sơ nhân viên liên kết đúng tài khoản
        và kỳ lương thể hiện trạng thái đã xác nhận hoặc đã chi tương ứng.
        Đánh dấu đã chi chỉ ghi nhận kết quả, không tự chuyển tiền.</p>
        <h2>Khi nhân viên không thấy chấm công</h2><p>Kiểm tra liên kết
        tài khoản, lịch và điểm làm việc đã phân công.</p>
        """,
    ),
    (
        "admin-user-accounts",
        "Tra cứu và xử lý tài khoản người dùng",
        "Đối chiếu đúng người và hồ sơ trước khi cập nhật hoặc khóa tài khoản.",
        "administration",
        ("SUPER_ADMIN",),
        86,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi hỗ trợ một tài khoản hoặc cần
        kiểm tra người gửi hồ sơ. Chuẩn bị email hay mã hồ sơ để đối chiếu.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/users">Người dùng</a> và tìm theo email
        hoặc thông tin đã được cung cấp.</li>
        <li>Mở đúng tài khoản, đối chiếu người sở hữu và hồ sơ liên quan.
        Kiểm tra trạng thái, phiên bản và tài liệu trước khi xử lý.</li>
        <li>Nếu hồ sơ thiếu thông tin, gửi yêu cầu bổ sung để người nộp
        tự cập nhật. Nếu cần khóa tài khoản, ghi rõ căn cứ và lý do.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Kiểm tra lại trạng thái tài khoản và
        hồ sơ sau thao tác; đối chiếu thông báo gửi cho người dùng khi có.</p>
        <h2>Khi không tìm thấy tài khoản</h2><p>Kiểm tra lại email, mã hồ sơ
        và bộ lọc trước khi tạo hay sửa bất kỳ tài khoản nào.</p>
        """,
    ),
    (
        "admin-publish-content",
        "Kiểm tra và công bố nội dung",
        "Xem trước các trường công khai và kiểm tra trang sau khi xuất bản.",
        "administration",
        ("SUPER_ADMIN",),
        87,
        """
        <h2>Khi nào dùng?</h2><p>Chỉ công bố khi hồ sơ đã hoàn tất các bước
        xét duyệt và nội dung dành cho công chúng đã được kiểm tra.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/content">Nội dung công bố</a> và chọn
        hồ sơ đủ điều kiện.</li>
        <li>Kiểm tra tiêu đề, mô tả, hình đại diện, danh mục và địa điểm.
        Loại bỏ thông tin riêng tư khỏi các trường công khai.</li>
        <li>Xem trước trên màn hình rộng và điện thoại, rồi công bố khi
        nội dung chính xác.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Mở trang công khai và đối chiếu nội dung
        vừa xuất bản với bản đã duyệt.</p>
        <h2>Khi nội dung chưa xuất hiện</h2><p>Kiểm tra trạng thái công bố
        và bản xem trước trước khi thử thao tác lại.</p>
        """,
    ),
    (
        "admin-audit-reports",
        "Kiểm tra lịch sử hoạt động và báo cáo",
        "Lọc bản ghi, đối chiếu thao tác và theo dõi khối lượng công việc.",
        "administration",
        ("SUPER_ADMIN",),
        88,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi cần xác định ai đã thao tác,
        thời điểm thực hiện hoặc xem tổng hợp công việc.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/audit">Lịch sử hoạt động</a>. Lọc theo
        thời gian, người thực hiện hoặc loại hoạt động.</li>
        <li>Mở bản ghi liên quan và đối chiếu với hồ sơ gốc trước khi
        kết luận. Ghi lại kết quả kiểm tra theo quy trình của đơn vị.</li>
        <li>Mở <a href="/admin/reports">Báo cáo</a> để xem số liệu tổng hợp
        và đối chiếu với các trường hợp cụ thể khi cần.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Bản ghi cần tìm hiển thị đúng người,
        thời điểm và đối tượng. Số liệu báo cáo được đối chiếu với phạm vi
        thời gian đã chọn.</p>
        <h2>Khi không tìm thấy bản ghi</h2><p>Mở rộng khoảng thời gian,
        bỏ bộ lọc và kiểm tra lại mã hồ sơ hoặc tài khoản.</p>
        """,
    ),
    (
        "admin-work-allocations",
        "Giao hồ sơ thẩm định và đầu việc chung",
        "Chọn hồ sơ hoặc mục tiêu công việc, người thực hiện và hạn hoàn thành.",
        "administration",
        ("SUPER_ADMIN",),
        89,
        """
        <h2>Khi nào dùng?</h2><p>Dùng để giao hồ sơ đã nộp cần thẩm định
        hoặc đầu việc chung cho người kiểm duyệt đang hoạt động.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/work-allocations">Phân công công việc</a>
        và chọn loại việc cần giao.</li>
        <li>Với hồ sơ thẩm định, chọn Hồ sơ cần thẩm định, đối chiếu mã,
        phiên bản và tài liệu rồi chọn người thẩm định, phạm vi công việc
        và hạn xử lý trước khi xác nhận phân công.</li>
        <li>Với đầu việc chung, nhập Mục tiêu công việc, mô tả nếu cần,
        Hạn hoàn thành, Mức độ ưu tiên và Người cùng thực hiện. Chọn
        Người phụ trách chính rồi bấm Giao công việc.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Việc vừa giao xuất hiện trong danh sách
        phân công và trong Công việc được giao của người nhận.</p>
        <h2>Nếu không có người để chọn</h2><p>Kiểm tra người kiểm duyệt
        đã chấp nhận lời mời và tài khoản đang hoạt động.</p>
        <h2>Hướng dẫn liên quan</h2><p>Xem
        <a href="/help/admin-review-assignments">Theo dõi thẩm định</a>.</p>
        """,
    ),
    (
        "admin-employee-requests",
        "Duyệt đơn nghỉ và yêu cầu tăng ca",
        "Kiểm tra thời gian, lý do và xác nhận quyết định cho từng yêu cầu.",
        "administration",
        ("SUPER_ADMIN",),
        90,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi nhân viên đã gửi đơn nghỉ hoặc
        yêu cầu tăng ca và trạng thái còn chờ quyết định.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/leave">Duyệt nghỉ phép</a> hoặc
        <a href="/admin/overtime">Duyệt tăng ca</a>.</li>
        <li>Mở yêu cầu, đối chiếu tên nhân viên, khoảng ngày hoặc giờ,
        loại nghỉ và lý do được cung cấp.</li>
        <li>Chọn Duyệt hoặc Từ chối. Kiểm tra lại thông tin trong hộp
        xác nhận, thêm Ghi chú quyết định khi cần rồi chọn Xác nhận duyệt
        hoặc Xác nhận từ chối.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Yêu cầu chuyển sang trạng thái đã duyệt
        hoặc từ chối; nhân viên nhận thông báo kết quả trong ứng dụng.</p>
        <h2>Khi chưa đủ căn cứ</h2><p>Đóng hộp xác nhận, đối chiếu lại lịch
        và thông tin với nhân viên trước khi quyết định.</p>
        """,
    ),
    (
        "admin-certificate-management",
        "Kiểm tra bằng xác lập đã phát hành",
        "Tra cứu bằng, kiểm tra hiển thị và mở yêu cầu điều chỉnh khi phù hợp.",
        "administration",
        ("SUPER_ADMIN",),
        91,
        """
        <h2>Khi nào dùng?</h2><p>Dùng để kiểm tra bằng đã phát hành,
        trạng thái công bố và phiên bản gắn với hồ sơ.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/certificates">Quản lý bằng xác lập</a>,
        tìm theo mã bằng hoặc mã hồ sơ rồi đối chiếu tên tác phẩm,
        trạng thái và phiên bản.</li>
        <li>Chọn Xác minh để xem thông tin tra cứu công khai. Nếu tác phẩm
        đã công bố, mở Nội dung công bố để kiểm tra trang liên quan.</li>
        <li>Mở Quản lý hiển thị và phiên bản. Với bằng đủ điều kiện,
        dùng Ẩn khỏi trang tác phẩm hoặc Cho hiển thị cùng tác phẩm.
        Chọn Tạo phiên bản điều chỉnh khi đã có thay đổi cần xử lý.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Kiểm tra lại trạng thái hiển thị trên
        trang tác phẩm và phiên bản bằng sau khi thao tác hoàn tất.</p>
        <h2>Khi tác phẩm chưa công bố</h2><p>Thay đổi hiển thị của bằng
        không tự công bố tác phẩm; kiểm tra quy trình công bố riêng.</p>
        """,
    ),
    (
        "admin-departments",
        "Quản lý cơ cấu phòng ban",
        "Tạo và cập nhật phòng ban dùng trong hồ sơ nhân viên.",
        "administration",
        ("SUPER_ADMIN",),
        92,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi cơ cấu phòng ban thay đổi
        trước khi gán phòng ban cho nhân viên.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/departments">Phòng ban</a> và kiểm tra
        danh sách hiện có để tránh tạo trùng.</li>
        <li>Chọn tạo phòng ban, nhập thông tin theo biểu mẫu rồi lưu.
        Kiểm tra phòng ban mới trong danh sách.</li>
        <li>Để sửa, mở phòng ban tương ứng, cập nhật thông tin và lưu;
        sau đó đối chiếu lại hồ sơ nhân viên liên quan.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Danh sách hiện thông tin mới và
        nhân viên được gán vào đúng phòng ban.</p>
        <h2>Nếu phòng ban không xuất hiện</h2><p>Tải lại danh sách,
        kiểm tra thông báo lỗi và tìm theo tên vừa nhập.</p>
        """,
    ),
    (
        "admin-send-announcement",
        "Gửi thông báo trong ứng dụng",
        "Chọn người nhận, kiểm tra số tài khoản và xác nhận nội dung trước khi gửi.",
        "administration",
        ("SUPER_ADMIN",),
        93,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi cần thông báo cho một tài khoản
        hoặc một nhóm người dùng. Thông báo sẽ xuất hiện trong ứng dụng
        của người nhận.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/notifications">Gửi thông báo</a>. Trong
        Chọn phạm vi gửi, chọn nhóm phù hợp; nếu gửi cho một người,
        tìm và chọn đúng tài khoản.</li>
        <li>Nhập Tiêu đề và Nội dung. Kiểm tra thông tin trước khi tiếp tục.</li>
        <li>Chọn Xem số người nhận, đối chiếu con số và phạm vi. Đánh dấu
        Tôi đã kiểm tra nội dung và phạm vi người nhận, rồi chọn Gửi thông báo.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Trang hiển thị số tài khoản đã nhận.
        Người nhận xem thông báo ở biểu tượng chuông và trang Thông báo.</p>
        <h2>Nếu chưa thể gửi</h2><p>Kiểm tra tiêu đề, nội dung, người nhận
        đã chọn và bước xác nhận. Nếu sửa nội dung, xem lại số người nhận
        trước khi gửi.</p>
        """,
    ),
    (
        "admin-community-reports",
        "Xử lý báo cáo nội dung cộng đồng",
        "Đọc báo cáo, đối chiếu nội dung và ghi lý do khi xử lý.",
        "administration",
        ("SUPER_ADMIN",),
        94,
        """
        <h2>Khi nào dùng?</h2><p>Dùng khi có báo cáo về bài viết hoặc
        bình luận trong cộng đồng. Chỉ mục phù hợp với quyền được cấp
        mới xuất hiện trong trang quản trị.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/admin/community">Kiểm duyệt cộng đồng</a>,
        chọn Báo cáo và mở nội dung được báo cáo.</li>
        <li>Đối chiếu nội dung gốc, người đăng, lý do báo cáo và thông tin
        người gửi. Nhập Lý do xử lý cho quyết định.</li>
        <li>Nếu báo cáo không có căn cứ, chọn Bỏ qua báo cáo. Nếu cần ẩn,
        chọn Ẩn nội dung và xử lý, đọc lại lý do rồi Xác nhận gỡ nội dung.</li>
        </ol>
        <h2>Kiểm tra kết quả</h2><p>Báo cáo không còn trong hàng đợi đang mở.
        Nội dung bị gỡ không còn hiển thị công khai; tác giả được thông báo
        kèm lý do.</p>
        <h2>Nếu báo cáo đã thay đổi</h2><p>Tải lại hàng đợi và mở bản
        mới nhất trước khi quyết định.</p>
        """,
    ),
    (
        "admin-sign-record",
        "Ghi nhận hồ sơ đã được phê duyệt",
        "Kiểm tra hồ sơ, dùng ví được cấp quyền và theo dõi xác nhận.",
        "administration",
        ("SUPER_ADMIN",),
        95,
        """
        <h2>Khi nào dùng?</h2><p>Chỉ ghi nhận hồ sơ đã hoàn tất xét duyệt
        và nghĩa vụ phí, bằng tài khoản và ví được tổ chức cấp quyền.</p>
        <h2>Cách thực hiện</h2><ol>
        <li>Mở <a href="/blockchain">Hồ sơ chờ ghi nhận</a> và chọn
        Kết nối ví. Kiểm tra ví đang dùng trước khi tiếp tục.</li>
        <li>Chọn hồ sơ trong hàng đợi, đối chiếu mã, tên tác phẩm,
        phiên bản và thông tin cần công bố ở bước Xác nhận trước khi ký.</li>
        <li>Xác nhận trong ví rồi theo dõi Tiến trình ký đến khi hệ thống
        báo đã ghi nhận. Kiểm tra mã giao dịch gắn với đúng hồ sơ.</li>
        </ol>
        <h2>Khi giao dịch đang chờ hoặc báo lỗi</h2><p>Nếu đã xác nhận
        trong ví, kiểm tra trạng thái hiện tại trước khi thao tác lại.
        Nếu có mã giao dịch nhưng chưa xác minh xong, dùng chức năng
        kiểm tra xác nhận thay vì ký thêm giao dịch.</p>
        <h2>Kiểm tra kết quả</h2><p>Hồ sơ thể hiện trạng thái đã ghi nhận
        cùng mã giao dịch để đối chiếu.</p>
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
                "id": UUID(f"11111111-1111-4111-8111-{0x200 + index:012x}"),
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
    op.get_bind().execute(
        sa.text(
            "DELETE FROM cms_guide_articles WHERE slug IN "
            f"({', '.join(f':slug_{index}' for index in range(len(slugs)))}) "
            "AND created_by IS NULL AND updated_by IS NULL AND version = 1"
        ),
        {f"slug_{index}": slug for index, slug in enumerate(slugs)},
    )
