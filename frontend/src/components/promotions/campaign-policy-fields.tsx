import type { CampaignInput, PromotionPolicy } from "@/lib/api/promotion-types";
import {
  Check,
  Choice,
  dateInput,
  dateValue,
  Field,
  optionalNumber,
  TextField,
} from "./form-fields";
import styles from "./promotions.module.css";

const services = [
  ["DOSSIER_SUBMISSION", "Phí nộp hồ sơ"],
  ["DOSSIER_APPROVAL", "Phí sau phê duyệt"],
  ["MEMBERSHIP", "Gói hội viên"],
  ["ADVERTISING", "Quảng cáo"],
] as const;
export function CampaignPolicyFields({
  step,
  value,
  update,
  policy,
}: {
  step: number;
  value: CampaignInput;
  update: (patch: Partial<CampaignInput>) => void;
  policy: (patch: Partial<PromotionPolicy>) => void;
}) {
  const rule = value.policy;
  const audience = rule.audience;
  if (step === 1)
    return (
      <div className={styles.stack}>
        <Choice
          label="Loại giảm giá"
          value={rule.discountType}
          onChange={(e) =>
            policy({
              discountType: e.target.value as PromotionPolicy["discountType"],
            })
          }
        >
          <option value="FIXED">Số tiền cố định</option>
          <option value="PERCENT">Theo phần trăm</option>
        </Choice>
        <div className={styles.grid}>
          <TextField
            label="Giá trị danh nghĩa / giảm cố định (VND)"
            type="number"
            min={1}
            required
            value={value.amountVnd}
            onChange={(e) => update({ amountVnd: Number(e.target.value) })}
          />
          {rule.discountType === "PERCENT" && (
            <>
              <TextField
                label="Phần trăm giảm (%)"
                type="number"
                min={0.01}
                max={100}
                step={0.01}
                value={rule.percentageBps / 100}
                onChange={(e) =>
                  policy({
                    percentageBps: Math.round(Number(e.target.value) * 100),
                  })
                }
              />
              <TextField
                label="Giảm tối đa (VND)"
                type="number"
                min={1}
                value={rule.discountCapVnd ?? ""}
                onChange={(e) =>
                  policy({ discountCapVnd: optionalNumber(e.target.value) })
                }
              />
            </>
          )}
          <TextField
            label="Đơn tối thiểu (VND)"
            type="number"
            min={0}
            value={rule.minimumOrderVnd}
            onChange={(e) =>
              policy({ minimumOrderVnd: Number(e.target.value) })
            }
          />
          <TextField
            label="Đơn tối đa (để trống nếu không giới hạn)"
            type="number"
            min={1}
            value={rule.maximumOrderVnd ?? ""}
            onChange={(e) =>
              policy({ maximumOrderVnd: optionalNumber(e.target.value) })
            }
          />
        </div>
        <Check
          label="Chỉ giao dịch đầu tiên"
          checked={rule.firstOrderOnly}
          onChange={(checked) =>
            policy({ firstOrderOnly: checked, subsequentOrderOnly: false })
          }
        />
        <Check
          label="Chỉ các giao dịch tiếp theo"
          checked={rule.subsequentOrderOnly}
          onChange={(checked) =>
            policy({ subsequentOrderOnly: checked, firstOrderOnly: false })
          }
        />
      </div>
    );
  if (step === 2)
    return (
      <div className={styles.stack}>
        <p className={styles.muted}>
          Chỉ áp dụng vào dịch vụ mua hàng. Nạp ví, rút tiền và chuyển tiền luôn
          bị loại.
        </p>
        {services.map(([code, label]) => (
          <Check
            key={code}
            label={label}
            checked={rule.serviceCodes.includes(code)}
            onChange={(checked) =>
              policy({
                serviceCodes: checked
                  ? [...rule.serviceCodes, code]
                  : rule.serviceCodes.filter((item) => item !== code),
              })
            }
          />
        ))}
        <Field label="ID gói cụ thể (mỗi dòng một ID, để trống để áp dụng mọi gói)">
          <textarea
            value={rule.productIds.join("\n")}
            onChange={(e) =>
              policy({
                productIds: e.target.value.split(/\s+/).filter(Boolean),
              })
            }
          />
        </Field>
      </div>
    );
  if (step === 3)
    return (
      <div className={styles.stack}>
        <p className={styles.muted}>
          Chỉ khách hàng USER không có hồ sơ nhân viên. Backend sẽ kiểm tra lại
          đối tượng khi phát và sử dụng.
        </p>
        <Choice
          label="Kết hợp điều kiện"
          value={audience.mode}
          onChange={(e) =>
            policy({
              audience: { ...audience, mode: e.target.value as "ALL" | "ANY" },
            })
          }
        >
          <option value="ALL">Thỏa tất cả điều kiện (AND)</option>
          <option value="ANY">Thỏa ít nhất một điều kiện (OR)</option>
        </Choice>
        <div className={styles.grid}>
          <TextField
            label="Đăng ký trước (cutoff)"
            type="datetime-local"
            value={dateInput(audience.registeredBefore)}
            onChange={(e) =>
              policy({
                audience: {
                  ...audience,
                  registeredBefore: dateValue(e.target.value),
                },
              })
            }
          />
          <TextField
            label="Đăng ký từ"
            type="datetime-local"
            value={dateInput(audience.registeredAfter)}
            onChange={(e) =>
              policy({
                audience: {
                  ...audience,
                  registeredAfter: dateValue(e.target.value),
                },
              })
            }
          />
        </div>
        <Choice
          label="Lịch sử mua dịch vụ"
          value={audience.purchaseHistory}
          onChange={(e) =>
            policy({
              audience: {
                ...audience,
                purchaseHistory: e.target
                  .value as typeof audience.purchaseHistory,
              },
            })
          }
        >
          <option value="ANY">Tất cả</option>
          <option value="FIRST">Chưa mua dịch vụ</option>
          <option value="RETURNING">Đã mua dịch vụ</option>
        </Choice>
        <div className={styles.grid}>
          {[
            ["MEMBER", "Đồng"],
            ["SILVER", "Bạc"],
            ["COMPANION", "Vàng"],
            ["PRESTIGE", "Kim cương"],
          ].map(([tier, label]) => (
            <Check
              key={tier}
              label={`Hạng ${label}`}
              checked={audience.membershipTiers.includes(tier!)}
              onChange={(checked) =>
                policy({
                  audience: {
                    ...audience,
                    membershipTiers: checked
                      ? [...audience.membershipTiers, tier!]
                      : audience.membershipTiers.filter(
                          (item) => item !== tier,
                        ),
                  },
                })
              }
            />
          ))}
        </div>
        <Field label="Danh sách ID người nhận (mỗi dòng một UUID)">
          <textarea
            value={audience.userIds.join("\n")}
            onChange={(e) =>
              policy({
                audience: {
                  ...audience,
                  userIds: e.target.value.split(/\s+/).filter(Boolean),
                },
              })
            }
          />
        </Field>
      </div>
    );
  if (step === 4)
    return (
      <div className={styles.stack}>
        <div className={styles.grid}>
          <TextField
            label="Bắt đầu chiến dịch"
            type="datetime-local"
            value={dateInput(value.startsAt)}
            onChange={(e) => update({ startsAt: dateValue(e.target.value) })}
          />
          <TextField
            label="Kết thúc chiến dịch"
            type="datetime-local"
            value={dateInput(value.endsAt)}
            onChange={(e) => update({ endsAt: dateValue(e.target.value) })}
          />
          <TextField
            label="Số ngày hiệu lực từ khi cấp"
            type="number"
            min={1}
            max={3660}
            value={value.validityDays}
            onChange={(e) => update({ validityDays: Number(e.target.value) })}
          />
          <TextField
            label="Hoặc hạn dùng cố định"
            type="datetime-local"
            value={dateInput(rule.fixedExpiresAt)}
            onChange={(e) =>
              policy({ fixedExpiresAt: dateValue(e.target.value) })
            }
          />
        </div>
        <Check
          label="Voucher đã cấp còn dùng được sau khi ngừng phát"
          checked={rule.allowUseAfterEnd}
          onChange={(checked) => policy({ allowUseAfterEnd: checked })}
        />
        <Check
          label="Cho phép khôi phục voucher khi hoàn tiền theo chính sách"
          checked={rule.restoreOnRefund}
          onChange={(checked) => policy({ restoreOnRefund: checked })}
        />
      </div>
    );
  return (
    <div className={styles.stack}>
      <div className={styles.grid}>
        {(
          [
            ["budgetVnd", "Ngân sách tối đa (VND)"],
            ["issuanceLimit", "Tổng số voucher được cấp"],
            ["redemptionLimit", "Tổng lượt sử dụng"],
            ["dailyLimit", "Lượt sử dụng tối đa mỗi ngày"],
            ["userDiscountLimitVnd", "Giảm tối đa mỗi người (VND)"],
          ] as const
        ).map(([key, label]) => (
          <TextField
            key={key}
            label={label}
            type="number"
            min={1}
            value={rule[key] ?? ""}
            onChange={(e) => policy({ [key]: optionalNumber(e.target.value) })}
          />
        ))}
        <TextField
          label="Số voucher mỗi tài khoản"
          type="number"
          min={1}
          max={100}
          value={rule.vouchersPerUser ?? 1}
          onChange={(e) => policy({ vouchersPerUser: Number(e.target.value) })}
        />
        <TextField
          label="Số lần sử dụng mỗi voucher"
          type="number"
          min={1}
          max={100}
          value={rule.usesPerVoucher}
          onChange={(e) => policy({ usesPerVoucher: Number(e.target.value) })}
        />
      </div>
      <Choice
        label="Kết hợp với ưu đãi hội viên"
        value={rule.stackingPolicy}
        onChange={(e) =>
          policy({
            stackingPolicy: e.target.value as PromotionPolicy["stackingPolicy"],
          })
        }
      >
        <option value="NONE">Không cộng dồn</option>
        <option value="BEST">Chọn ưu đãi có lợi nhất</option>
        <option value="MEMBERSHIP_FIRST">Ưu tiên ưu đãi hội viên</option>
      </Choice>
      <p className={styles.muted}>
        Mỗi đơn chỉ dùng một voucher. Giá trị đã cấp, khoản đang giữ và giảm giá
        đã sử dụng được theo dõi riêng.
      </p>
    </div>
  );
}
