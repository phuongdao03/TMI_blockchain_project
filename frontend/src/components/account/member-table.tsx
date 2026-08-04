"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { LoaderCircle, MailPlus, Trash2, UsersRound } from "lucide-react";
import { useForm } from "react-hook-form";

import { FormField } from "@/components/auth/form-field";
import { Button } from "@/components/ui/button";
import type { MemberInput, OrganizationMember } from "@/lib/api/types";
import { memberSchema, type MemberValues } from "@/lib/account/schemas";

interface MemberTableProps {
  members: OrganizationMember[];
  ownerUserId: string;
  canManage: boolean;
  onAdd: (member: MemberInput) => Promise<void>;
  onRemove: (userId: string) => Promise<void>;
}

const roleLabels = {
  OWNER: "Chủ sở hữu",
  ORG_MANAGER: "Quản lý",
  MEMBER: "Thành viên",
} as const;

const statusLabels = {
  ACTIVE: "Đang hoạt động",
  INVITED: "Đã mời",
} as const;

export function MemberTable({
  members,
  ownerUserId,
  canManage,
  onAdd,
  onRemove,
}: MemberTableProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MemberValues>({
    resolver: zodResolver(memberSchema),
    defaultValues: { email: "", roleCode: "MEMBER" },
  });

  const submit = handleSubmit(async (values) => {
    await onAdd({ ...values, status: "INVITED" });
    reset();
  });

  return (
    <div className="space-y-5">
      {canManage ? (
        <form
          className="grid gap-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4 md:grid-cols-[minmax(0,1fr)_12rem_auto] md:items-end"
          noValidate
          onSubmit={submit}
        >
          <FormField
            autoComplete="email"
            error={errors.email?.message}
            label="Email thành viên"
            placeholder="member@tmigroup.vn"
            type="email"
            {...register("email")}
          />
          <div className="space-y-2">
            <label
              className="block text-sm font-semibold text-neutral-700"
              htmlFor="member-role"
            >
              Vai trò
            </label>
            <select
              className="min-h-12 w-full rounded-xl border border-neutral-200 bg-white px-3.5 text-sm font-medium text-neutral-950 focus:border-primary-600 focus:ring-3 focus:ring-primary-100"
              id="member-role"
              {...register("roleCode")}
            >
              <option value="MEMBER">Thành viên</option>
              <option value="ORG_MANAGER">Quản lý</option>
            </select>
          </div>
          <Button disabled={isSubmitting} type="submit">
            {isSubmitting ? (
              <LoaderCircle
                aria-hidden="true"
                className="size-4 animate-spin"
              />
            ) : (
              <MailPlus aria-hidden="true" className="size-4" />
            )}
            Mời thành viên
          </Button>
        </form>
      ) : (
        <p className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-600">
          Chỉ chủ sở hữu hoặc quản lý tổ chức có thể thay đổi thành viên.
        </p>
      )}

      <div className="overflow-hidden rounded-2xl border border-neutral-200">
        <div className="flex items-center gap-2 border-b border-neutral-200 bg-neutral-50 px-4 py-3">
          <UsersRound aria-hidden="true" className="size-4 text-primary-700" />
          <p className="text-sm font-semibold">{members.length} thành viên</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[38rem] text-left text-sm">
            <thead className="text-xs uppercase tracking-wider text-neutral-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Tài khoản</th>
                <th className="px-4 py-3 font-semibold">Vai trò</th>
                <th className="px-4 py-3 font-semibold">Trạng thái</th>
                <th className="px-4 py-3 text-right font-semibold">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {members.map((member) => (
                <tr key={member.userId}>
                  <td className="px-4 py-4 font-medium text-neutral-950">
                    {member.email}
                  </td>
                  <td className="px-4 py-4 text-neutral-600">
                    {roleLabels[member.roleCode]}
                  </td>
                  <td className="px-4 py-4">
                    <span
                      className={
                        member.status === "ACTIVE"
                          ? "rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700"
                          : "rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700"
                      }
                    >
                      {statusLabels[member.status]}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right">
                    {canManage && member.userId !== ownerUserId ? (
                      <Button
                        aria-label={`Xóa ${member.email}`}
                        className="min-h-9 px-3 text-error hover:bg-primary-50"
                        onClick={() => void onRemove(member.userId)}
                        variant="ghost"
                      >
                        <Trash2 aria-hidden="true" className="size-4" />
                      </Button>
                    ) : (
                      <span className="text-xs text-neutral-400">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
