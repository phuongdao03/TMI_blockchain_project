"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ApiError, communityMemberApi, membershipApi } from "@/lib/api/client";
import type { MembershipBenefitCode, MembershipTier } from "@/lib/api/types";

const tierRank: Record<MembershipTier, number> = {
  MEMBER: 0,
  SILVER: 1,
  COMPANION: 2,
  PRESTIGE: 3,
};

const benefitOptions: {
  value: MembershipBenefitCode;
  label: string;
  description: string;
  diamondOnly: boolean;
}[] = [
  {
    value: "COLLABORATION_NEED",
    label: "Đăng nhu cầu hợp tác",
    description:
      "Gửi nhu cầu để quản trị viên duyệt và hiển thị trong không gian kết nối hội viên Vàng, Kim cương.",
    diamondOnly: false,
  },
  {
    value: "ADVISORY_SESSION",
    label: "Đặt buổi tư vấn 30 phút",
    description:
      "Tối đa một yêu cầu được tiếp nhận trong mỗi chu kỳ hội viên Kim cương.",
    diamondOnly: true,
  },
  {
    value: "FACILITATED_INTRODUCTION",
    label: "Đề xuất kết nối có điều phối",
    description:
      "Tối đa hai yêu cầu trong mỗi chu kỳ; kết nối cần sự đồng ý của các bên.",
    diamondOnly: true,
  },
  {
    value: "MEMBER_STORY",
    label: "Gửi câu chuyện hội viên",
    description:
      "Gửi nội dung để Ban biên tập xem xét; gửi yêu cầu không đồng nghĩa được đăng.",
    diamondOnly: true,
  },
];

const statusLabel: Record<string, string> = {
  PENDING: "Đang chờ tiếp nhận",
  INFO_REQUESTED: "Cần bổ sung thông tin",
  APPROVED: "Đã tiếp nhận, đang điều phối",
  COMPLETED: "Đã hoàn tất",
  REJECTED: "Không được tiếp nhận",
};

export function MembershipBenefitCenter({ tier }: { tier: MembershipTier }) {
  const client = useQueryClient();
  const enabled = tierRank[tier] >= tierRank.COMPANION;
  const requests = useQuery({
    queryKey: ["membership-benefit-requests"],
    queryFn: membershipApi.myBenefitRequests,
    enabled,
  });
  const needs = useQuery({
    queryKey: ["membership-collaboration-needs"],
    queryFn: membershipApi.collaborationNeeds,
    enabled,
  });
  const [benefit, setBenefit] =
    useState<MembershipBenefitCode>("COLLABORATION_NEED");
  const [statement, setStatement] = useState("");
  const [directoryDraft, setDirectoryDraft] = useState("");
  const [directorySearch, setDirectorySearch] = useState("");
  const canSearchMembers = tierRank[tier] >= tierRank.COMPANION;
  const directory = useQuery({
    queryKey: ["membership-member-directory", directorySearch],
    queryFn: ({ signal }) =>
      communityMemberApi.directory(directorySearch, signal),
    enabled: canSearchMembers && directorySearch.length >= 2,
  });
  const submit = useMutation({
    mutationFn: () => membershipApi.submitBenefitRequest(benefit, statement),
    onSuccess: async () => {
      setStatement("");
      await client.invalidateQueries({
        queryKey: ["membership-benefit-requests"],
      });
    },
  });

  if (!enabled) return null;
  const options = benefitOptions.filter(
    (option) => !option.diamondOnly || tier === "PRESTIGE",
  );
  const selected =
    options.find((option) => option.value === benefit) ?? options[0];

  return (
    <section
      aria-labelledby="membership-benefit-center-heading"
      className="space-y-6 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6"
      id="membership-benefits"
    >
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-[var(--theme-accent)]">
          Quyền lợi cần điều phối
        </p>
        <h2
          className="mt-2 text-xl font-bold sm:text-2xl"
          id="membership-benefit-center-heading"
        >
          Gửi yêu cầu quyền lợi
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--theme-muted)]">
          Yêu cầu được lưu theo chu kỳ hội viên và chuyển vào hàng đợi quản trị.
          Quyền lợi có hạn mức được kiểm tra ở máy chủ.
        </p>
      </header>

      <form
        className="grid gap-4 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit.mutate();
        }}
      >
        <label className="text-sm font-semibold sm:col-span-2">
          Loại yêu cầu
          <select
            className="mt-2 min-h-12 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base"
            value={benefit}
            onChange={(event) =>
              setBenefit(event.target.value as MembershipBenefitCode)
            }
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <span className="mt-1 block font-normal leading-6 text-[var(--theme-muted)]">
            {selected?.description}
          </span>
        </label>
        <label className="text-sm font-semibold sm:col-span-2">
          Nội dung
          <textarea
            className="mt-2 min-h-32 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 py-3 text-base leading-6"
            maxLength={5000}
            minLength={1}
            placeholder="Nêu mục tiêu, bối cảnh và thông tin cần thiết để xử lý yêu cầu."
            required
            value={statement}
            onChange={(event) => setStatement(event.target.value)}
          />
          <span className="mt-1 block text-xs font-normal text-[var(--theme-muted)]">
            {statement.length}/5.000 ký tự
          </span>
          {benefit === "COLLABORATION_NEED" ? (
            <span className="mt-2 block text-xs font-normal leading-5 text-[var(--theme-muted)]">
              Nội dung sau khi được duyệt sẽ hiển thị với hội viên Vàng và Kim
              cương. Không nhập email, số điện thoại hoặc thông tin riêng tư.
            </span>
          ) : null}
        </label>
        <Button
          className="w-full sm:col-span-2 sm:w-fit"
          disabled={submit.isPending || !statement.trim()}
          type="submit"
        >
          {submit.isPending ? "Đang gửi…" : "Gửi yêu cầu"}
        </Button>
        {submit.isError ? (
          <p className="text-sm text-red-700 sm:col-span-2" role="alert">
            {submit.error instanceof ApiError
              ? submit.error.message
              : "Chưa thể gửi yêu cầu. Vui lòng thử lại."}
          </p>
        ) : null}
        {submit.isSuccess ? (
          <p className="text-sm text-emerald-700 sm:col-span-2" role="status">
            Yêu cầu đã được gửi vào hàng đợi xử lý.
          </p>
        ) : null}
      </form>

      <div className="grid gap-6 lg:grid-cols-2">
        <section aria-labelledby="my-benefit-requests-heading">
          <h3 className="font-bold" id="my-benefit-requests-heading">
            Yêu cầu của tôi
          </h3>
          {requests.isPending ? (
            <p className="mt-3 text-sm text-[var(--theme-muted)]" role="status">
              Đang tải yêu cầu…
            </p>
          ) : requests.isError ? (
            <p className="mt-3 text-sm text-red-700" role="alert">
              Chưa thể tải lịch sử yêu cầu.
            </p>
          ) : requests.data.requests.length ? (
            <ul className="mt-3 divide-y divide-[var(--theme-border)]">
              {requests.data.requests.map((request) => (
                <li className="space-y-2 py-3" key={request.id}>
                  <div className="flex flex-wrap justify-between gap-2 text-sm">
                    <strong>{benefitLabel(request.benefit)}</strong>
                    <span>{statusLabel[request.status]}</span>
                  </div>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-[var(--theme-muted)]">
                    {request.statement}
                  </p>
                  {request.decisionNote ? (
                    <p className="text-sm leading-6">
                      Phản hồi: {request.decisionNote}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-[var(--theme-muted)]">
              Bạn chưa gửi yêu cầu nào.
            </p>
          )}
        </section>

        <section aria-labelledby="collaboration-needs-heading">
          <h3 className="font-bold" id="collaboration-needs-heading">
            Nhu cầu hợp tác đã duyệt
          </h3>
          {needs.isPending ? (
            <p className="mt-3 text-sm text-[var(--theme-muted)]" role="status">
              Đang tải nhu cầu…
            </p>
          ) : needs.isError ? (
            <p className="mt-3 text-sm text-red-700" role="alert">
              Chưa thể tải không gian kết nối.
            </p>
          ) : needs.data.requests.length ? (
            <ul className="mt-3 space-y-3">
              {needs.data.requests.map((need) => (
                <li
                  className="rounded-xl border border-[var(--theme-border)] p-4"
                  key={need.id}
                >
                  <p className="font-semibold">{need.displayName}</p>
                  {need.username ? (
                    <p className="text-xs text-[var(--theme-muted)]">
                      @{need.username}
                    </p>
                  ) : null}
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
                    {need.statement}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-[var(--theme-muted)]">
              Chưa có nhu cầu nào được duyệt để kết nối.
            </p>
          )}
        </section>
      </div>

      {canSearchMembers ? (
        <section
          aria-labelledby="member-directory-heading"
          className="space-y-4"
        >
          <div>
            <h3 className="font-bold" id="member-directory-heading">
              Tìm hội viên theo lĩnh vực
            </h3>
            <p className="mt-1 text-sm leading-6 text-[var(--theme-muted)]">
              Chỉ tìm thấy hội viên đã công khai lĩnh vực hoạt động trong hồ sơ.
            </p>
          </div>
          <form
            className="flex flex-col gap-3 sm:flex-row"
            onSubmit={(event) => {
              event.preventDefault();
              const query = directoryDraft.trim();
              if (query.length < 2) return;
              if (query === directorySearch) void directory.refetch();
              else setDirectorySearch(query);
            }}
          >
            <label className="sr-only" htmlFor="member-directory-query">
              Từ khóa tìm hội viên
            </label>
            <input
              autoComplete="off"
              className="min-h-12 min-w-0 flex-1 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] px-3 text-base"
              id="member-directory-query"
              maxLength={120}
              minLength={2}
              onChange={(event) => setDirectoryDraft(event.target.value)}
              placeholder="Ví dụ: thiết kế, nông nghiệp, giáo dục"
              required
              value={directoryDraft}
            />
            <Button className="min-h-12 w-full sm:w-auto" type="submit">
              Tìm hội viên
            </Button>
          </form>
          {directorySearch.length === 0 ? (
            <p className="text-sm text-[var(--theme-muted)]">
              Nhập ít nhất 2 ký tự để bắt đầu tìm kiếm.
            </p>
          ) : directory.isPending ? (
            <p className="text-sm text-[var(--theme-muted)]" role="status">
              Đang tìm hội viên…
            </p>
          ) : directory.isError ? (
            <p className="text-sm text-red-700" role="alert">
              Chưa thể tìm hội viên. Vui lòng thử lại.
            </p>
          ) : directory.data.members.length ? (
            <>
              <p className="text-sm text-[var(--theme-muted)]" role="status">
                Tìm thấy {directory.data.total} hội viên.
              </p>
              <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {directory.data.members.map((member) => (
                  <li key={member.id}>
                    <Link
                      className="flex min-h-full gap-3 rounded-xl border border-[var(--theme-border)] p-4 transition hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]"
                      href={`/community/members/${encodeURIComponent(member.username)}`}
                    >
                      <span
                        aria-hidden="true"
                        className="flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[var(--theme-elevated)] text-sm font-bold"
                      >
                        {member.displayName.slice(0, 1)}
                      </span>
                      <span className="min-w-0">
                        <strong className="block truncate">
                          {member.displayName}
                        </strong>
                        <span className="block truncate text-xs text-[var(--theme-muted)]">
                          @{member.username}
                        </span>
                        {member.professionalTitle || member.organization ? (
                          <span className="mt-2 block text-sm leading-5">
                            {[member.professionalTitle, member.organization]
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        ) : null}
                        {member.activityFields ? (
                          <span className="mt-1 block text-sm leading-5 text-[var(--theme-muted)]">
                            {member.activityFields}
                          </span>
                        ) : null}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-sm text-[var(--theme-muted)]" role="status">
              Chưa có hội viên công khai lĩnh vực phù hợp với từ khóa này.
            </p>
          )}
        </section>
      ) : null}
    </section>
  );
}

export function benefitLabel(benefit: MembershipBenefitCode): string {
  return (
    benefitOptions.find((option) => option.value === benefit)?.label ?? benefit
  );
}
