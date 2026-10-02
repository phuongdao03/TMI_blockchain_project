"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  BadgeCheck,
  BriefcaseBusiness,
  Camera,
  LoaderCircle,
  Save,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/auth/form-field";
import { FileUploader } from "@/components/media/file-uploader";
import { Button } from "@/components/ui/button";
import type { ProfileUpdate, UserProfile } from "@/lib/api/types";
import { profileSchema, type ProfileValues } from "@/lib/account/schemas";

interface ProfileFormProps {
  avatarLinkPending?: boolean;
  onAvatarUploaded: (mediaId: string) => void;
  profile: UserProfile;
  onSave: (profile: ProfileUpdate) => Promise<void>;
}

const employmentStatusLabel: Record<string, string> = {
  ACTIVE: "Đang làm việc",
  ON_LEAVE: "Đang nghỉ phép",
  INACTIVE: "Tạm ngừng",
  TERMINATED: "Đã nghỉ việc",
};

export function ProfileForm({
  avatarLinkPending = false,
  onAvatarUploaded,
  profile,
  onSave,
}: ProfileFormProps) {
  const [saved, setSaved] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      fullName: profile.fullName ?? "",
      phone: profile.phone?.replace(/^\+84/, "0") ?? "",
      locale: profile.locale,
      timezone: profile.timezone,
    },
  });

  const submit = handleSubmit(async (values) => {
    setSaved(false);
    await onSave({
      fullName: values.fullName || null,
      phone: values.phone || null,
      locale: values.locale,
      timezone: values.timezone,
    });
    setSaved(true);
  });

  return (
    <form className="space-y-6" noValidate onSubmit={submit}>
      <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-5 sm:flex-row sm:items-center">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-primary-100 text-primary-700">
          <UserRound aria-hidden="true" className="size-6" />
        </span>
        <div className="min-w-0">
          <p className="text-lg font-bold text-neutral-950">
            {profile.fullName || "Hồ sơ cá nhân"}
          </p>
          <p className="break-all text-sm text-neutral-700">{profile.email}</p>
          <p className="mt-1 text-xs text-neutral-500">
            {profile.avatarMediaId
              ? "Ảnh đại diện đã được liên kết"
              : "Chưa có ảnh đại diện"}
          </p>
        </div>
      </div>

      {profile.employment ? (
        <section
          className="rounded-2xl border border-neutral-200 p-5"
          aria-label="Thông tin công việc"
        >
          <div className="flex flex-wrap items-center gap-2 text-primary-700">
            <BriefcaseBusiness aria-hidden="true" className="size-5" />
            <h3 className="font-bold">Thông tin công việc</h3>
            <span className="rounded-full bg-primary-50 px-2.5 py-1 text-xs font-semibold">
              {employmentStatusLabel[profile.employment.employmentStatus] ??
                profile.employment.employmentStatus}
            </span>
          </div>
          <p className="mt-1 text-xs text-neutral-500">
            Thông tin do quản trị viên cập nhật. Họ tên và số điện thoại của bạn
            có thể sửa bên dưới.
          </p>
          <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-neutral-500">Mã nhân viên</dt>
              <dd className="mt-1 font-semibold text-neutral-950">
                {profile.employment.employeeCode}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500">Phòng ban</dt>
              <dd className="mt-1 font-semibold text-neutral-950">
                {profile.employment.departmentName}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500">Vị trí</dt>
              <dd className="mt-1 font-semibold text-neutral-950">
                {profile.employment.position}
              </dd>
            </div>
            <div>
              <dt className="text-neutral-500">Ngày vào làm</dt>
              <dd className="mt-1 font-semibold text-neutral-950">
                {new Intl.DateTimeFormat("vi-VN", { timeZone: "UTC" }).format(
                  new Date(profile.employment.joinDate),
                )}
              </dd>
            </div>
          </dl>
        </section>
      ) : null}

      <details className="rounded-2xl border border-neutral-200 p-4">
        <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-neutral-950">
          <Camera aria-hidden="true" className="size-4" /> Thay ảnh đại diện
        </summary>
        <div className="mt-4">
          <FileUploader
            disabled={avatarLinkPending}
            label="Ảnh đại diện"
            onComplete={(asset) => onAvatarUploaded(asset.id)}
            purpose="AVATAR"
          />
        </div>
      </details>

      {saved ? (
        <p
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800"
          role="status"
        >
          <BadgeCheck aria-hidden="true" className="size-4" />
          Hồ sơ đã được cập nhật.
        </p>
      ) : null}

      <div className="grid gap-5 md:grid-cols-2">
        <FormField
          autoComplete="name"
          error={errors.fullName?.message}
          label="Họ và tên"
          placeholder="Nguyễn Minh Anh"
          {...register("fullName")}
        />
        <FormField
          autoComplete="tel"
          error={errors.phone?.message}
          hint="Nhập số Việt Nam bắt đầu bằng 0."
          label="Số điện thoại"
          inputMode="tel"
          placeholder="0901234567"
          {...register("phone")}
        />
      </div>

      <details className="rounded-2xl border border-neutral-200 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-neutral-950">
          Ngôn ngữ và múi giờ
        </summary>
        <div className="mt-4 grid gap-5 md:grid-cols-2">
          <FormField
            error={errors.locale?.message}
            label="Ngôn ngữ"
            {...register("locale")}
          />
          <FormField
            error={errors.timezone?.message}
            label="Múi giờ"
            {...register("timezone")}
          />
        </div>
      </details>

      <div className="flex justify-end border-t border-neutral-100 pt-5">
        <Button disabled={isSubmitting} type="submit">
          {isSubmitting ? (
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin" />
          ) : (
            <Save aria-hidden="true" className="size-4" />
          )}
          {isSubmitting ? "Đang lưu…" : "Lưu hồ sơ"}
        </Button>
      </div>
    </form>
  );
}
