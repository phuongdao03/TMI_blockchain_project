"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, LoaderCircle, Save, UserRound } from "lucide-react";
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
      phone: profile.phone ?? "",
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
      <div className="flex flex-col gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4 sm:flex-row sm:items-center">
        <span className="grid size-16 shrink-0 place-items-center rounded-2xl bg-ink-950 text-white shadow-lg shadow-slate-950/15">
          <UserRound aria-hidden="true" className="size-7" />
        </span>
        <div>
          <p className="font-semibold text-neutral-950">
            {profile.fullName || "Hồ sơ cá nhân"}
          </p>
          <p className="mt-1 text-sm text-neutral-500">
            {profile.avatarMediaId
              ? "Ảnh đại diện đã được liên kết"
              : "Chưa có ảnh đại diện"}
          </p>
        </div>
      </div>

      <FileUploader
        disabled={avatarLinkPending}
        label="Ảnh đại diện"
        onComplete={(asset) => onAvatarUploaded(asset.id)}
        purpose="AVATAR"
      />

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
          hint="Dùng mã quốc gia, ví dụ +84."
          label="Số điện thoại"
          placeholder="+84901234567"
          {...register("phone")}
        />
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
