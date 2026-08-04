"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Building2, LoaderCircle, Save } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import type { Organization, OrganizationInput } from "@/lib/api/types";
import {
  organizationSchema,
  type OrganizationValues,
} from "@/lib/account/schemas";

interface OrganizationFormProps {
  organization?: Organization;
  canEdit: boolean;
  onSave: (organization: OrganizationInput) => Promise<void>;
}

export function OrganizationForm({
  organization,
  canEdit,
  onSave,
}: OrganizationFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<OrganizationValues>({
    resolver: zodResolver(organizationSchema),
    defaultValues: {
      code: organization?.code ?? "",
      legalName: organization?.legalName ?? "",
      displayName: organization?.displayName ?? "",
      taxCode: organization?.taxCode ?? "",
    },
  });

  const submit = handleSubmit(async (values) => {
    await onSave({ ...values, taxCode: values.taxCode || null });
  });

  return (
    <form className="space-y-5" noValidate onSubmit={submit}>
      <div className="flex items-start gap-3 rounded-2xl bg-ink-950 p-4 text-white">
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-white/10 text-gold-300">
          <Building2 aria-hidden="true" className="size-5" />
        </span>
        <div>
          <p className="font-semibold">
            {organization?.displayName ?? "Tạo không gian tổ chức"}
          </p>
          <p className="mt-1 text-sm leading-6 text-slate-400">
            Thông tin pháp lý và mã số thuế chỉ hiển thị cho người có quyền quản
            lý.
          </p>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <FormField
          disabled={!canEdit || Boolean(organization)}
          error={errors.code?.message}
          hint={organization ? "Mã tổ chức không thể thay đổi." : undefined}
          label="Mã tổ chức"
          placeholder="TMI-LAB"
          {...register("code")}
        />
        <FormField
          disabled={!canEdit}
          error={errors.displayName?.message}
          label="Tên hiển thị"
          {...register("displayName")}
        />
        <FormField
          className="md:col-span-2"
          disabled={!canEdit}
          error={errors.legalName?.message}
          label="Tên pháp lý"
          {...register("legalName")}
        />
        <FormField
          disabled={!canEdit}
          error={errors.taxCode?.message}
          label="Mã số thuế"
          {...register("taxCode")}
        />
      </div>

      {canEdit ? (
        <div className="flex justify-end border-t border-neutral-100 pt-5">
          <Button disabled={isSubmitting} type="submit">
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-4 animate-spin"
              />
            ) : (
              <Save aria-hidden="true" className="size-4" />
            )}
            {organization ? "Lưu tổ chức" : "Tạo tổ chức"}
          </Button>
        </div>
      ) : null}
    </form>
  );
}
