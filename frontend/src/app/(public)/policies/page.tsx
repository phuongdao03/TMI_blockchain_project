import { PolicyGuide } from "@/components/public/platform-guidance";

export default function PoliciesPage() {
  return (
    <div className="process-page public-policy-page">
      <header className="public-page-header">
        <div className="public-page-header__content">
          <p>ĐIỀU KHOẢN &amp; QUYỀN RIÊNG TƯ</p>
          <h1>Điều khoản sử dụng &amp; Chính sách quyền riêng tư.</h1>
          <p>
            Quy định về việc sử dụng nền tảng, quản lý hồ sơ, xử lý dữ liệu cá
            nhân, công bố thông tin và tra cứu chứng thư.
          </p>
          <span>Cập nhật lần cuối: 24/08/2026</span>
        </div>
      </header>
      <PolicyGuide />
    </div>
  );
}
