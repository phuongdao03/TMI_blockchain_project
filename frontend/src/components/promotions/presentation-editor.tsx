import type { PromotionPresentation } from "@/lib/api/promotion-types";
import { Check, Choice, TextField } from "./form-fields";
import styles from "./promotions.module.css";

export function PresentationEditor({
  value,
  onChange,
}: {
  value: PromotionPresentation;
  onChange: (patch: Partial<PromotionPresentation>) => void;
}) {
  return (
    <div className={styles.stack}>
      <div className={styles.grid}>
        <Choice
          label="Mẫu popup"
          value={value.template}
          onChange={(e) =>
            onChange({
              template: e.target.value as PromotionPresentation["template"],
            })
          }
        >
          <option value="GIFT">Gift Celebration — Quà tri ân</option>
          <option value="PREMIUM">Premium Voucher — Phiếu ưu đãi</option>
          <option value="MINIMAL">Minimal Offer — Tối giản</option>
          <option value="LIMITED">Limited Time — Có thời hạn</option>
        </Choice>
        <Choice
          label="Nhận diện"
          value={value.theme}
          onChange={(e) => {
            const theme = e.target.value as PromotionPresentation["theme"];
            onChange({
              theme,
              ...(theme === "PREMIUM"
                ? {
                    backgroundColor: "#261111",
                    textColor: "#fff9f3",
                    ctaColor: "#9d0000",
                  }
                : theme === "MINIMAL"
                  ? {
                      backgroundColor: "#ffffff",
                      textColor: "#241515",
                      ctaColor: "#9d0000",
                    }
                  : {
                      backgroundColor: "#fff9ed",
                      textColor: "#671b16",
                      ctaColor: "#9d0000",
                    }),
            });
          }}
        >
          <option value="CLASSIC">Tinh Hoa Classic</option>
          <option value="LIGHT">Tinh Hoa Light</option>
          <option value="PREMIUM">Tinh Hoa Premium</option>
          <option value="MINIMAL">Minimal Modern</option>
        </Choice>
      </div>
      <TextField
        label="Phụ đề"
        value={value.subtitle}
        maxLength={200}
        onChange={(e) => onChange({ subtitle: e.target.value })}
      />
      <div className={styles.grid}>
        <TextField
          label="Nút chính"
          value={value.primaryCta}
          maxLength={60}
          onChange={(e) => onChange({ primaryCta: e.target.value })}
        />
        <TextField
          label="Nút phụ"
          value={value.secondaryCta}
          maxLength={60}
          onChange={(e) => onChange({ secondaryCta: e.target.value })}
        />
      </div>
      <TextField
        label="Mô tả ảnh cho người dùng trình đọc màn hình"
        value={value.altText}
        onChange={(e) => onChange({ altText: e.target.value })}
      />
      <div className={styles.grid}>
        {(
          [
            ["backgroundColor", "Màu nền"],
            ["textColor", "Màu chữ"],
            ["ctaColor", "Màu CTA"],
          ] as const
        ).map(([key, label]) => (
          <TextField
            key={key}
            label={label}
            type="color"
            value={value[key]}
            onChange={(e) => onChange({ [key]: e.target.value })}
          />
        ))}
        <TextField
          label="Bo góc (px)"
          type="number"
          min={0}
          max={32}
          value={value.borderRadius}
          onChange={(e) => onChange({ borderRadius: Number(e.target.value) })}
        />
        <TextField
          label="Độ tối nền phía sau"
          type="number"
          min={0}
          max={0.8}
          step={0.05}
          value={value.overlay}
          onChange={(e) => onChange({ overlay: Number(e.target.value) })}
        />
      </div>
      <Choice
        label="Cách hiển thị ảnh"
        value={value.imageFit}
        onChange={(e) =>
          onChange({ imageFit: e.target.value as "contain" | "cover" })
        }
      >
        <option value="contain">Giữ trọn ảnh</option>
        <option value="cover">Lấp đầy khung</option>
      </Choice>
      <div className={styles.grid}>
        <TextField
          label="Tâm ảnh ngang (%)"
          type="range"
          min={0}
          max={100}
          value={value.focalX}
          onChange={(e) => onChange({ focalX: Number(e.target.value) })}
        />
        <TextField
          label="Tâm ảnh dọc (%)"
          type="range"
          min={0}
          max={100}
          value={value.focalY}
          onChange={(e) => onChange({ focalY: Number(e.target.value) })}
        />
      </div>
      <Choice
        label="Thời điểm hiển thị"
        value={value.trigger}
        onChange={(e) =>
          onChange({
            trigger: e.target.value as PromotionPresentation["trigger"],
          })
        }
      >
        {[
          ["LOGIN", "Sau đăng nhập"],
          ["DASHBOARD", "Trang chủ / không gian cá nhân"],
          ["ISSUED", "Vừa được cấp voucher"],
          ["CHECKOUT", "Thanh toán đủ điều kiện"],
          ["NOTIFICATION", "Mở thông báo"],
          ["BANNER", "Banner cố định"],
        ].map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </Choice>
      <Choice
        label="Tần suất"
        value={value.frequency}
        onChange={(e) =>
          onChange({
            frequency: e.target.value as PromotionPresentation["frequency"],
          })
        }
      >
        <option value="ONCE">Một lần</option>
        <option value="SESSION">Mỗi phiên</option>
        <option value="LIMITED">Giới hạn số lần</option>
      </Choice>
      <div className={styles.grid}>
        <TextField
          label="Số lần hiển thị tối đa"
          type="number"
          min={1}
          max={100}
          value={value.maxViews}
          onChange={(e) => onChange({ maxViews: Number(e.target.value) })}
        />
        <TextField
          label="Khoảng nghỉ giữa các lần (giờ)"
          type="number"
          min={0}
          max={8760}
          value={value.cooldownHours}
          onChange={(e) => onChange({ cooldownHours: Number(e.target.value) })}
        />
      </div>
      <Check
        label="Bật hiển thị popup"
        checked={value.enabled}
        onChange={(enabled) => onChange({ enabled })}
      />
      <Check
        label="Gửi thông báo trong ứng dụng khi cấp"
        checked={value.notifyInApp}
        onChange={(notifyInApp) => onChange({ notifyInApp })}
      />
    </div>
  );
}
