"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { promotionApi } from "@/lib/api/client";
import {
  newCampaign,
  type CampaignInput,
  type PromotionCampaign,
  type PromotionPolicy,
} from "@/lib/api/promotion-types";
import { CampaignPolicyFields } from "./campaign-policy-fields";
import { Choice, Field, readableError, TextField } from "./form-fields";
import { PromotionMediaLibrary } from "./promotion-media-library";
import { PromotionPreview } from "./promotion-preview";
import { PresentationEditor } from "./presentation-editor";
import styles from "./promotions.module.css";

export function CampaignBuilder({
  id,
  presentationOnly = false,
}: {
  id?: string;
  presentationOnly?: boolean;
}) {
  const campaign = useQuery({
    queryKey: ["promotions", "detail", id],
    queryFn: () => promotionApi.detail(id!),
    enabled: Boolean(id),
  });
  if (id && campaign.isPending)
    return <p role="status">Đang tải chiến dịch…</p>;
  if (id && campaign.isError)
    return (
      <p role="alert" className={styles.error}>
        {readableError(campaign.error)}
      </p>
    );
  return (
    <CampaignEditor
      key={id ?? "new"}
      initial={campaign.data}
      presentationOnly={presentationOnly}
    />
  );
}

const steps = [
  "Thông tin",
  "Giá trị",
  "Dịch vụ",
  "Đối tượng",
  "Hiệu lực",
  "Giới hạn",
  "Thiết kế popup",
  "Xem lại",
];
function CampaignEditor({
  initial,
  presentationOnly,
}: {
  initial?: PromotionCampaign;
  presentationOnly: boolean;
}) {
  const router = useRouter();
  const client = useQueryClient();
  const [value, setValue] = useState<CampaignInput>(() =>
    initial
      ? {
          code: initial.code,
          name: initial.name,
          internalDescription: initial.internalDescription,
          title: initial.title,
          description: initial.description,
          terms: initial.terms,
          imagePath: initial.imagePath,
          amountVnd: initial.amountVnd,
          validityDays: initial.validityDays,
          startsAt: initial.startsAt,
          endsAt: initial.endsAt,
          programType: initial.programType,
          policy: initial.policy,
        }
      : newCampaign(),
  );
  const [step, setStep] = useState(presentationOnly ? 6 : 0);
  const [mobile, setMobile] = useState(false);
  const [saved, setSaved] = useState(false);
  const [imageSlot, setImageSlot] = useState<
    | "imageAssetId"
    | "mobileImageAssetId"
    | "cardImageAssetId"
    | "thumbnailAssetId"
  >("imageAssetId");
  const update = (patch: Partial<CampaignInput>) => {
    setSaved(false);
    setValue((previous) => ({ ...previous, ...patch }));
  };
  const policy = (patch: Partial<PromotionPolicy>) => {
    setSaved(false);
    setValue((previous) => ({
      ...previous,
      policy: { ...previous.policy, ...patch },
    }));
  };
  const save = useMutation({
    mutationFn: () =>
      initial
        ? promotionApi.update(initial.id, value)
        : promotionApi.create(value),
    onSuccess: async (campaign) => {
      setSaved(true);
      await client.invalidateQueries({ queryKey: ["promotions"] });
      if (!initial) router.replace(`/admin/promotions/${campaign.id}/edit`);
    },
  });
  const locked = Boolean(
    initial && !["DRAFT", "SCHEDULED"].includes(initial.status),
  );
  return (
    <div className={styles.two}>
      <div className={styles.panel}>
        <h2>{initial ? initial.name : "Tạo chiến dịch mới"}</h2>
        {!presentationOnly && (
          <nav aria-label="Các bước tạo chiến dịch" className={styles.steps}>
            {steps.map((label, index) => (
              <button
                type="button"
                key={label}
                aria-current={step === index ? "step" : undefined}
                onClick={() => setStep(index)}
              >
                {index + 1}. {label}
              </button>
            ))}
          </nav>
        )}
        {locked && step < 6 && (
          <p className={styles.muted}>
            Chiến dịch đã xuất bản: điều kiện cốt lõi được giữ nguyên để bảo vệ
            voucher đã cấp. Sao chép chiến dịch để tạo chính sách mới.
          </p>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
          className={styles.stack}
        >
          <fieldset disabled={locked && step < 6} className={styles.stack}>
            {step === 0 && (
              <>
                <TextField
                  label="Tên chiến dịch"
                  required
                  maxLength={255}
                  value={value.name}
                  onChange={(e) => update({ name: e.target.value })}
                />
                <TextField
                  label="Mã chiến dịch"
                  required
                  pattern={"[A-Z0-9_\\-]+"}
                  maxLength={64}
                  value={value.code}
                  onChange={(e) =>
                    update({ code: e.target.value.toUpperCase() })
                  }
                />
                <Field label="Mô tả nội bộ">
                  <textarea
                    value={value.internalDescription}
                    onChange={(e) =>
                      update({ internalDescription: e.target.value })
                    }
                  />
                </Field>
                <TextField
                  label="Tiêu đề hiển thị"
                  required
                  maxLength={255}
                  value={value.title}
                  onChange={(e) => update({ title: e.target.value })}
                />
                <Field label="Nội dung hiển thị">
                  <textarea
                    required
                    value={value.description}
                    onChange={(e) => update({ description: e.target.value })}
                  />
                </Field>
                <Field label="Điều kiện ngắn">
                  <textarea
                    required
                    value={value.terms}
                    onChange={(e) => update({ terms: e.target.value })}
                  />
                </Field>
                <Choice
                  label="Phương thức phát"
                  value={value.programType}
                  onChange={(e) =>
                    update({
                      programType: e.target
                        .value as CampaignInput["programType"],
                    })
                  }
                >
                  <option value="CLAIM">Khách hàng tự nhận</option>
                  <option value="AUTO">Tự động cho người đủ điều kiện</option>
                  <option value="CODE">Nhập mã khuyến mại</option>
                  <option value="MANUAL">Admin phát thủ công</option>
                  <option value="FIRST_ORDER">Ưu đãi đơn đầu tiên</option>
                </Choice>
                {value.programType === "CODE" && (
                  <TextField
                    label="Mã khuyến mại công khai"
                    required
                    pattern={"[A-Z0-9_\\-]+"}
                    value={value.policy.publicCode ?? ""}
                    onChange={(e) =>
                      policy({ publicCode: e.target.value.toUpperCase() })
                    }
                  />
                )}
              </>
            )}
            {step > 0 && step < 6 && (
              <CampaignPolicyFields
                step={step}
                value={value}
                update={update}
                policy={policy}
              />
            )}
            {step === 6 && (
              <>
                <PresentationEditor
                  value={value.policy.presentation}
                  onChange={(patch) =>
                    policy({
                      presentation: { ...value.policy.presentation, ...patch },
                    })
                  }
                />
                <h3 className="font-semibold">Ảnh minh họa</h3>
                <Choice
                  label="Vị trí ảnh"
                  value={imageSlot}
                  onChange={(e) =>
                    setImageSlot(e.target.value as typeof imageSlot)
                  }
                >
                  <option value="imageAssetId">Popup desktop</option>
                  <option value="mobileImageAssetId">Popup mobile</option>
                  <option value="cardImageAssetId">Thẻ voucher</option>
                  <option value="thumbnailAssetId">Ảnh thu nhỏ</option>
                </Choice>
                <PromotionMediaLibrary
                  selectMode
                  onSelect={(asset) => {
                    if (imageSlot === "imageAssetId")
                      update({ imagePath: asset.url });
                    policy({
                      presentation: {
                        ...value.policy.presentation,
                        [imageSlot]: asset.id,
                        altText: asset.altText,
                      },
                    });
                  }}
                />
              </>
            )}
            {step === 7 && (
              <div className={styles.stack}>
                <h3 className="font-semibold">Kiểm tra trước khi xuất bản</h3>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <dt>Mã</dt>
                  <dd>{value.code}</dd>
                  <dt>Dịch vụ</dt>
                  <dd>{value.policy.serviceCodes.join(", ")}</dd>
                  <dt>Đối tượng</dt>
                  <dd>USER không có hồ sơ nhân viên</dd>
                  <dt>Cutoff</dt>
                  <dd>
                    {value.policy.audience.registeredBefore ?? "Không đặt"}
                  </dd>
                  <dt>Ngân sách</dt>
                  <dd>
                    {value.policy.budgetVnd?.toLocaleString("vi-VN") ??
                      "Không giới hạn"}
                  </dd>
                  <dt>Thông báo</dt>
                  <dd>
                    {value.policy.presentation.notifyInApp
                      ? "Trong ứng dụng"
                      : "Tắt"}
                  </dd>
                </dl>
                <p className={styles.muted}>
                  Lưu chiến dịch trước, sau đó dùng nút Xuất bản trong danh
                  sách. Hệ thống sẽ kiểm tra điều kiện, ngày cutoff và ngân sách
                  trên backend.
                </p>
              </div>
            )}
          </fieldset>
          {save.isError && (
            <p role="alert" className={styles.error}>
              {readableError(save.error)}
            </p>
          )}
          {saved && (
            <p role="status" className={styles.success}>
              Đã lưu chiến dịch.
            </p>
          )}
          <div className={styles.actions}>
            {!presentationOnly && step > 0 && (
              <Button variant="ghost" onClick={() => setStep(step - 1)}>
                Bước trước
              </Button>
            )}
            {!presentationOnly && step < 7 && (
              <Button variant="outline" onClick={() => setStep(step + 1)}>
                Tiếp theo
              </Button>
            )}
            <Button type="submit" disabled={save.isPending}>
              {save.isPending
                ? "Đang lưu…"
                : initial
                  ? "Lưu thay đổi"
                  : "Lưu nháp"}
            </Button>
          </div>
        </form>
      </div>
      <aside className={styles.preview} aria-label="Xem trước chiến dịch">
        <div className={`${styles.actions} mb-4`}>
          <Button
            variant={mobile ? "outline" : "default"}
            onClick={() => setMobile(false)}
          >
            Desktop
          </Button>
          <Button
            variant={mobile ? "default" : "outline"}
            onClick={() => setMobile(true)}
          >
            Mobile
          </Button>
        </div>
        <PromotionPreview campaign={value} mobile={mobile} />
      </aside>
    </div>
  );
}
