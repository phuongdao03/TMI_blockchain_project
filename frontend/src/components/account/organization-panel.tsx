"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { MemberTable } from "@/components/account/member-table";
import { OrganizationForm } from "@/components/account/organization-form";
import { ApiError, organizationApi } from "@/lib/api/client";
import type {
  MemberInput,
  Organization,
  OrganizationInput,
} from "@/lib/api/types";

interface OrganizationPanelProps {
  organizations: Organization[];
}

export function OrganizationPanel({ organizations }: OrganizationPanelProps) {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState(organizations[0]?.id);
  const selected =
    organizations.find((organization) => organization.id === selectedId) ??
    organizations[0];
  const membersQuery = useQuery({
    queryKey: ["organizations", selected?.id, "members"],
    queryFn: () => organizationApi.listMembers(selected!.id),
    enabled: Boolean(selected),
  });

  const saveMutation = useMutation({
    mutationFn: async (values: OrganizationInput) =>
      selected
        ? organizationApi.update(selected.id, values)
        : organizationApi.create(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
  const addMutation = useMutation({
    mutationFn: (member: MemberInput) =>
      organizationApi.addMember(selected!.id, member),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["organizations", selected?.id, "members"],
      });
    },
  });
  const removeMutation = useMutation({
    mutationFn: (userId: string) =>
      organizationApi.removeMember(selected!.id, userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["organizations", selected?.id, "members"],
      });
    },
  });

  const error = saveMutation.error ?? addMutation.error ?? removeMutation.error;

  return (
    <div className="space-y-6">
      {organizations.length > 1 ? (
        <div className="max-w-sm space-y-2">
          <label
            className="block text-sm font-semibold text-neutral-700"
            htmlFor="organization-select"
          >
            Tổ chức đang quản lý
          </label>
          <select
            className="min-h-12 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 text-sm font-semibold focus:border-primary-600 focus:ring-3 focus:ring-primary-100"
            id="organization-select"
            onChange={(event) => setSelectedId(event.target.value)}
            value={selected?.id}
          >
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.displayName}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {error ? (
        <p
          className="rounded-xl border border-error bg-primary-50 p-3 text-sm font-medium text-error"
          role="alert"
        >
          {error instanceof ApiError
            ? error.message
            : "Không thể cập nhật tổ chức lúc này. Vui lòng thử lại."}
        </p>
      ) : null}

      <OrganizationForm
        canEdit={!selected || selected.canManageMembers}
        key={selected?.id ?? "new"}
        onSave={async (values) => {
          await saveMutation.mutateAsync(values);
        }}
        organization={selected}
      />

      {selected ? (
        <section className="border-t border-neutral-100 pt-6">
          <div className="mb-4">
            <h3 className="text-base font-semibold">Thành viên tổ chức</h3>
            <p className="mt-1 text-sm text-neutral-500">
              Mỗi thành viên chỉ nhìn thấy phần việc được giao và có thể được
              cập nhật bất cứ lúc nào.
            </p>
          </div>
          {membersQuery.isPending ? (
            <p className="py-8 text-center text-sm text-neutral-500">
              Đang tải danh sách thành viên…
            </p>
          ) : membersQuery.isError ? (
            <p className="rounded-xl bg-primary-50 p-3 text-sm text-error">
              Không thể tải danh sách thành viên.
            </p>
          ) : (
            <MemberTable
              canManage={selected.canManageMembers}
              members={membersQuery.data.data}
              onAdd={async (member) => {
                await addMutation.mutateAsync(member);
              }}
              onRemove={async (userId) => {
                await removeMutation.mutateAsync(userId);
              }}
              ownerUserId={selected.ownerUserId}
            />
          )}
        </section>
      ) : null}
    </div>
  );
}
