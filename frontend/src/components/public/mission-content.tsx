import Image from "next/image";

const objectives = [
  {
    number: "01",
    title: "Giới thiệu cách ghi nhận giá trị",
    detail:
      "Làm rõ cách tiếp nhận, xem xét và ghi nhận hồ sơ theo tiêu chí, quy trình đã được phê duyệt; bảo đảm minh bạch, có căn cứ và có thể kiểm chứng.",
  },
  {
    number: "02",
    title: "Ghi nhận những đóng góp có chiều sâu",
    detail:
      "Tìm hiểu và ghi nhận những đóng góp của con người, tổ chức, sản phẩm, tri thức, văn hóa và sáng tạo Việt Nam; phân biệt rõ đề cử và xác lập.",
  },
  {
    number: "03",
    title: "Phát triển hạ tầng số",
    detail:
      "Xây dựng hạ tầng số Tinh Hoa Việt để lưu trữ hồ sơ, chia sẻ câu chuyện, kết nối cộng đồng và tiếp tục phát huy giá trị được ghi nhận.",
  },
  {
    number: "04",
    title: "Mở rộng những hành trình tiếp nối",
    detail:
      "Phát triển Hành trình Tìm kiếm giá trị Tinh Hoa Việt và Hành trình Du lịch Tinh Hoa Việt, tạo thêm cơ hội khám phá, kết nối và lan tỏa trong các giai đoạn tiếp theo.",
  },
  {
    number: "05",
    title: "Kết nối các bên đồng hành",
    detail:
      "Tăng cường hợp tác với hiệp hội, viện nghiên cứu, cơ sở giáo dục, cơ quan báo chí, doanh nghiệp và đối tác phù hợp trên nguyên tắc tự nguyện, minh bạch, đúng chức năng.",
  },
] as const;

export function MissionContent() {
  return (
    <section
      aria-labelledby="mission-title"
      className="mission-section"
      id="muc-tieu-chuong-trinh"
    >
      <div className="mission-section__inner">
        <div className="mission-section__story">
          <p className="mission-section__eyebrow">
            Giới thiệu chương trình Tinh Hoa Việt
          </p>
          <h2 id="mission-title">
            Nhận diện giá trị Việt. <span>Nuôi dưỡng hành trình dài.</span>
          </h2>
          <p className="mission-section__lead">
            Tinh Hoa Việt là chương trình hướng tới việc tìm kiếm, ghi nhận và
            lan tỏa những giá trị Việt có chiều sâu. Từ con người, tổ chức và
            sản phẩm đến tri thức, văn hóa và sáng tạo, mỗi giá trị được tiếp
            cận bằng tinh thần khoa học, minh bạch và tôn trọng. Chương trình
            mong muốn kết nối những đóng góp ấy với cộng đồng và tạo điều kiện
            để chúng tiếp tục được gìn giữ, phát huy theo thời gian.
          </p>
          <figure className="mission-section__seal">
            <Image
              alt=""
              height={256}
                loading="eager"
              sizes="112px"
              src="/assets/brand/logo-tinh-hoa-viet.png"
              width={256}
            />
          </figure>
          <div className="mission-section__invitation">
            <p className="mission-section__eyebrow">Lời mời đồng hành</p>
            <p>
              Chúng tôi trân trọng mời Quý Doanh nghiệp cùng xây dựng không gian
              nhận diện, chia sẻ và lưu giữ những giá trị Việt có chiều sâu. Sự
              đồng hành góp phần phát triển hạ tầng, mở rộng kết nối và duy trì
              những hoạt động tiếp nối của chương trình.
            </p>
            <p className="mission-section__principle">
              Quyền lợi đồng hành được công bố minh bạch. Việc tài trợ không
              trao quyền can thiệp vào kết quả đề cử, thẩm định hoặc xác lập;
              Hội đồng xem xét kết quả chuyên môn theo quy trình đã phê duyệt.
              Chương trình không cam kết thay cho thị trường hay quyết định của
              Hội đồng. Chúng tôi cam kết triển khai nghiêm túc và trân trọng
              từng đóng góp.
            </p>
          </div>
        </div>

        <div className="mission-section__objectives">
          <div className="mission-section__objectives-heading">
            <p className="mission-section__eyebrow">Định hướng phát triển</p>
            <h3>Năm trọng tâm của chương trình</h3>
          </div>
          <ol>
            {objectives.map((objective) => (
              <li key={objective.number}>
                <span className="mission-section__number" aria-hidden="true">
                  {objective.number}
                </span>
                <div>
                  <h4>{objective.title}</h4>
                  <p>{objective.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
