"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { communityAdminApi } from "@/lib/api/client";
import type {
  CommunityAdminCategory,
  CommunityAdminCategoryCreateInput,
  CommunityAdminCategoryUpdateInput,
  CommunityAdminSettings,
  CommunityModerationTargetType,
  CommunityReport,
  CommunityReportReason,
  CommunityTargetType,
} from "@/lib/api/types";

const PAGE_SIZE = 20;

export function CommunityReportQueue() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const reportsKey = ["community", "admin", "reports", "OPEN", page] as const;
  const reports = useQuery({
    queryKey: reportsKey,
    queryFn: ({ signal }) => communityAdminApi.reports({ page, status: "OPEN" }, signal),
  });
  const resolve = useMutation({
    mutationFn: ({ reportId, action, reason }: {
      reportId: string;
      action: "HIDE" | "DISMISS";
      reason: string;
    }) => communityAdminApi.resolveReport(reportId, { action, reason }),
    onSuccess: async (_result, variables) => {
      setReasons((current) => ({ ...current, [variables.reportId]: "" }));
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["community", "admin", "reports"] }),
        queryClient.invalidateQueries({ queryKey: ["community", "admin", "moderation-history"] }),
      ]);
    },
  });
  const items = reports.data?.data ?? [];
  const totalPages = Math.max(1, Math.ceil((reports.data?.meta.total ?? 0) / (reports.data?.meta.pageSize || PAGE_SIZE)));

  function submitResolution(report: CommunityReport, action: "HIDE" | "DISMISS") {
    const reason = reasons[report.id]?.trim();
    if (!reason || resolve.isPending) return;
    resolve.mutate({ reportId: report.id, action, reason });
  }

  return (
    <section aria-busy={reports.isPending || resolve.isPending} aria-labelledby="community-report-queue-title">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-[var(--theme-border)] pb-4">
        <div>
          <p className="text-xs font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">An toàn cộng đồng</p>
          <h2 className="mt-2 text-2xl font-bold text-[var(--theme-text)]" id="community-report-queue-title">Báo cáo đang mở</h2>
        </div>
        {reports.data ? <p className="text-sm text-[var(--theme-muted)]">{reports.data.meta.total} báo cáo</p> : null}
      </header>
      {reports.isPending ? <PanelLoading label="Đang tải báo cáo" /> : null}
      {reports.isError ? <PanelError message="Chưa thể tải báo cáo cộng đồng." onRetry={() => void reports.refetch()} /> : null}
      {reports.data && items.length === 0 ? <PanelEmpty title="Chưa có báo cáo đang mở" body="Các báo cáo mới sẽ xuất hiện tại đây để người có quyền xem xét." /> : null}
      {items.length ? (
        <div className="space-y-4">
          {items.map((report) => (
            <ReportCard
              key={report.id}
              onReasonChange={(reason) => setReasons((current) => ({ ...current, [report.id]: reason }))}
              onResolve={(action) => submitResolution(report, action)}
              pending={resolve.isPending}
              reason={reasons[report.id] ?? ""}
              report={report}
            />
          ))}
        </div>
      ) : null}
      {resolve.isError ? <p className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm font-semibold text-red-900" role="alert">Không thể xử lý báo cáo. Nội dung có thể đã thay đổi; hãy tải lại hàng đợi.</p> : null}
      {totalPages > 1 ? (
        <nav aria-label="Phân trang báo cáo" className="mt-5 flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-4">
          <button className={secondaryClass} disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">Trang trước</button>
          <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">Trang {page} / {totalPages}</p>
          <button className={secondaryClass} disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} type="button">Trang sau</button>
        </nav>
      ) : null}
    </section>
  );
}

function ReportCard({ report, reason, pending, onReasonChange, onResolve }: {
  report: CommunityReport;
  reason: string;
  pending: boolean;
  onReasonChange: (reason: string) => void;
  onResolve: (action: "HIDE" | "DISMISS") => void;
}) {
  const preview = report.targetPreview;
  const targetHref = preview.type === "POST"
    ? `/community/posts/${encodeURIComponent(preview.slug)}`
    : `/community/posts/${encodeURIComponent(preview.postSlug)}#comment-${encodeURIComponent(preview.id)}`;
  const reporterName = report.reporter.displayName?.trim() || "Thành viên";
  const reasonId = `community-report-resolution-${report.id}`;

  return (
    <article className="rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--theme-muted)]">
        <span className="rounded-full bg-[var(--theme-elevated)] px-3 py-1 font-bold">{preview.type === "POST" ? "Bài viết" : "Bình luận"}</span>
        <span>{reportReasonLabel(report.reason)}</span>
        <time dateTime={report.createdAt}>{formatDate(report.createdAt)}</time>
      </div>
      <p className="mt-3 text-sm text-[var(--theme-muted)]">Người gửi: <Link className="font-semibold text-[var(--theme-text)] hover:text-[var(--theme-accent)]" href={`/community/members/${encodeURIComponent(report.reporter.username)}`}>{reporterName}</Link></p>
      <h3 className="mt-3 text-xl font-bold text-[var(--theme-text)]">
        <Link className="hover:text-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)]" href={targetHref}>
          {preview.type === "POST" ? preview.title : preview.postTitle}
        </Link>
      </h3>
      {preview.type === "POST" ? (
        <div className="mt-3 rounded-xl border border-[var(--theme-border)] p-4">
          <p className="text-xs text-[var(--theme-muted)]">Tác giả: {preview.author.displayName || "Thành viên"}</p>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)]">{preview.excerpt}</p>
        </div>
      ) : (
        <div className="mt-3 rounded-xl border border-[var(--theme-border)] p-4">
          <p className="text-xs text-[var(--theme-muted)]">Người bình luận: {preview.author?.displayName || (preview.isDeleted ? "Thành viên" : "Thành viên")}</p>
          <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)]">{preview.isDeleted ? "Bình luận đã bị xóa." : preview.content}</p>
        </div>
      )}
      <p className="mt-3 text-sm font-semibold text-[var(--theme-text)]">Lý do: {reportReasonLabel(report.reason)}</p>
      {report.details ? <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-muted)]">{report.details}</p> : null}
      <form className="mt-4 border-t border-[var(--theme-border)] pt-4" onSubmit={(event) => { event.preventDefault(); onResolve("HIDE"); }}>
        <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor={reasonId}>Lý do xử lý</label>
        <textarea className={textareaClass} id={reasonId} maxLength={2000} onChange={(event) => onReasonChange(event.target.value)} required value={reason} />
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button className={secondaryClass} disabled={!reason.trim() || pending} onClick={() => onResolve("DISMISS")} type="button">Bỏ qua báo cáo</button>
          <button className={primaryClass} disabled={!reason.trim() || pending} type="submit">Ẩn nội dung và xử lý</button>
        </div>
      </form>
    </article>
  );
}

export function CommunityVisibilityPanel() {
  const [targetType, setTargetType] = useState<CommunityTargetType>("POST");
  const [action, setAction] = useState<"hide" | "restore">("hide");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [notice, setNotice] = useState("");
  const visibility = useMutation({
    mutationFn: async () => {
      const input = { reason: reason.trim() };
      if (targetType === "POST") {
        return action === "hide"
          ? communityAdminApi.hidePost(targetId.trim(), input)
          : communityAdminApi.restorePost(targetId.trim(), input);
      }
      return action === "hide"
        ? communityAdminApi.hideComment(targetId.trim(), input)
        : communityAdminApi.restoreComment(targetId.trim(), input);
    },
    onSuccess: (result) => {
      setNotice(result.state === "HIDDEN" ? "Nội dung đã được ẩn." : "Nội dung đã được khôi phục.");
      setReason("");
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!targetId.trim() || !reason.trim() || visibility.isPending) return;
    setNotice("");
    visibility.mutate();
  }

  return (
    <section aria-labelledby="community-visibility-title" className="max-w-3xl">
      <h2 className="text-2xl font-bold text-[var(--theme-text)]" id="community-visibility-title">Ẩn hoặc khôi phục nội dung</h2>
      <p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">Chỉ thao tác với nội dung đã xác minh. Mỗi thay đổi cần có lý do lưu trong lịch sử kiểm duyệt.</p>
      <form className="mt-5 space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6" onSubmit={submit}>
        <div className="grid gap-4 sm:grid-cols-2">
          <FieldSelect label="Loại nội dung" onChange={(value) => setTargetType(value as CommunityTargetType)} value={targetType}>
            <option value="POST">Bài viết</option><option value="COMMENT">Bình luận</option>
          </FieldSelect>
          <FieldSelect label="Thao tác" onChange={(value) => setAction(value as "hide" | "restore")} value={action}>
            <option value="hide">Ẩn</option><option value="restore">Khôi phục</option>
          </FieldSelect>
        </div>
        <FieldInput label="Mã nội dung" onChange={setTargetId} value={targetId} />
        <FieldTextarea label="Lý do" onChange={setReason} value={reason} />
        {visibility.isError ? <p className="text-sm font-semibold text-red-700" role="alert">Không thể cập nhật trạng thái nội dung. Có thể nội dung không còn ở trạng thái phù hợp.</p> : null}
        {notice ? <p className="text-sm font-semibold text-[var(--theme-accent)]" role="status">{notice}</p> : null}
        <button className={primaryClass} disabled={!targetId.trim() || !reason.trim() || visibility.isPending} type="submit">{action === "hide" ? "Ẩn nội dung" : "Khôi phục nội dung"}</button>
      </form>
    </section>
  );
}

export function CommunityModerationHistoryPanel() {
  const [page, setPage] = useState(1);
  const [targetType, setTargetType] = useState<CommunityModerationTargetType | "">("");
  const [targetId, setTargetId] = useState("");
  const [applied, setApplied] = useState<{ targetType?: CommunityModerationTargetType; targetId?: string }>({});
  const queryKey = ["community", "admin", "moderation-history", applied.targetType ?? "", applied.targetId ?? "", page] as const;
  const history = useQuery({
    queryKey,
    queryFn: ({ signal }) => communityAdminApi.moderationHistory({
      ...(applied.targetType ? { targetType: applied.targetType } : {}),
      ...(applied.targetId ? { targetId: applied.targetId } : {}),
      page,
      pageSize: PAGE_SIZE,
    }, signal),
  });
  const events = history.data?.data ?? [];
  const totalPages = Math.max(1, Math.ceil((history.data?.meta.total ?? 0) / (history.data?.meta.pageSize || PAGE_SIZE)));

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setApplied({
      ...(targetType ? { targetType } : {}),
      ...(targetId.trim() ? { targetId: targetId.trim() } : {}),
    });
  }

  return (
    <section aria-busy={history.isPending} aria-labelledby="community-history-title">
      <header className="mb-5 border-b border-[var(--theme-border)] pb-4">
        <p className="text-xs font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">Nhật ký không thể chỉnh sửa</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--theme-text)]" id="community-history-title">Lịch sử kiểm duyệt</h2>
      </header>
      <form className="mb-5 grid gap-3 rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={applyFilters}>
        <FieldSelect label="Loại nội dung" onChange={(value) => setTargetType(value as CommunityModerationTargetType | "")} value={targetType}>
          <option value="">Tất cả</option><option value="POST">Bài viết</option><option value="COMMENT">Bình luận</option><option value="CATEGORY">Danh mục</option><option value="SETTINGS">Cài đặt</option>
        </FieldSelect>
        <FieldInput label="Mã nội dung" onChange={setTargetId} value={targetId} />
        <button className={secondaryClass} type="submit">Lọc lịch sử</button>
      </form>
      {history.isPending ? <PanelLoading label="Đang tải lịch sử kiểm duyệt" /> : null}
      {history.isError ? <PanelError message="Chưa thể tải lịch sử kiểm duyệt." onRetry={() => void history.refetch()} /> : null}
      {history.data && events.length === 0 ? <PanelEmpty title="Chưa có sự kiện" body="Các thay đổi có quyền kiểm duyệt sẽ được ghi lại tại đây." /> : null}
      {events.length ? <ol className="divide-y divide-[var(--theme-border)] rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)]">
        {events.map((event) => (
          <li className="grid gap-2 p-4 sm:grid-cols-[1fr_auto] sm:items-start sm:p-5" key={event.id}>
            <div className="min-w-0">
              <p className="font-bold text-[var(--theme-text)]">{event.action}</p>
              <p className="mt-1 break-words text-sm text-[var(--theme-muted)]">{event.targetType} · {event.targetId} · Người thực hiện {event.actor.displayName || event.actorId}</p>
              <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--theme-text)]">{event.reason}</p>
              <p className="mt-2 break-all text-xs text-[var(--theme-muted)]">Mã yêu cầu: {event.requestId}</p>
            </div>
            <time className="text-xs text-[var(--theme-muted)]" dateTime={event.createdAt}>{formatDate(event.createdAt)}</time>
          </li>
        ))}
      </ol> : null}
      {totalPages > 1 ? <nav aria-label="Phân trang lịch sử kiểm duyệt" className="mt-4 flex items-center justify-between gap-3 border-t border-[var(--theme-border)] py-4">
        <button className={secondaryClass} disabled={page <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button">Trang trước</button>
        <p aria-live="polite" className="text-sm text-[var(--theme-muted)]">Trang {page} / {totalPages}</p>
        <button className={secondaryClass} disabled={page >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} type="button">Trang sau</button>
      </nav> : null}
    </section>
  );
}

export function CommunityCategoryManagement() {
  const queryClient = useQueryClient();
  const categories = useQuery({
    queryKey: ["community", "admin", "categories"],
    queryFn: ({ signal }) => communityAdminApi.categories(signal),
  });
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newReason, setNewReason] = useState("");
  const [newIcon, setNewIcon] = useState("");
  const [newSortOrder, setNewSortOrder] = useState("0");
  const [newIsActive, setNewIsActive] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<CategoryDraft | null>(null);
  const [notice, setNotice] = useState("");
  const create = useMutation({
    mutationFn: (input: CommunityAdminCategoryCreateInput) => communityAdminApi.createCategory(input),
    onSuccess: async () => {
      setNewName(""); setNewSlug(""); setNewDescription(""); setNewReason(""); setNewIcon(""); setNewSortOrder("0"); setNewIsActive(true);
      setNotice("Danh mục đã được tạo.");
      await queryClient.invalidateQueries({ queryKey: ["community", "admin", "categories"] });
    },
  });
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: CommunityAdminCategoryUpdateInput }) => communityAdminApi.updateCategory(id, input),
    onSuccess: async () => {
      setEditingId(null); setEditDraft(null); setNotice("Danh mục đã được cập nhật.");
      await queryClient.invalidateQueries({ queryKey: ["community", "admin", "categories"] });
    },
  });

  function createCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newName.trim() || !newSlug.trim() || !newDescription.trim() || !newReason.trim()) return;
    create.mutate({
      name: newName.trim(),
      slug: newSlug.trim(),
      description: newDescription.trim(),
      ...(newIcon.trim() ? { icon: newIcon.trim() } : {}),
      sortOrder: Math.max(0, Number(newSortOrder) || 0),
      isActive: newIsActive,
      reason: newReason.trim(),
    });
  }

  function startEdit(category: CommunityAdminCategory) {
    setEditingId(category.id);
    setEditDraft({
      name: category.name,
      slug: category.slug,
      description: category.description ?? "",
      icon: category.icon ?? "",
      sortOrder: String(category.sortOrder),
      isActive: category.isActive,
      reason: "",
    });
  }

  function saveEdit(event: FormEvent<HTMLFormElement>, categoryId: string) {
    event.preventDefault();
    if (!editDraft || !editDraft.name.trim() || !editDraft.slug.trim() || !editDraft.description.trim() || !editDraft.reason.trim()) return;
    update.mutate({
      id: categoryId,
      input: {
        name: editDraft.name.trim(), slug: editDraft.slug.trim(), description: editDraft.description.trim(),
        icon: editDraft.icon.trim() || null,
        sortOrder: Math.max(0, Number(editDraft.sortOrder) || 0),
        isActive: editDraft.isActive,
        reason: editDraft.reason.trim(),
      },
    });
  }

  return (
    <section aria-labelledby="community-categories-title">
      <header className="mb-5 border-b border-[var(--theme-border)] pb-4">
        <p className="text-xs font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">Quản lý cấu trúc</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--theme-text)]" id="community-categories-title">Danh mục cộng đồng</h2>
      </header>
      <form className="grid gap-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:grid-cols-2 sm:p-6" onSubmit={createCategory}>
        <h3 className="text-lg font-bold text-[var(--theme-text)] sm:col-span-2">Tạo danh mục</h3>
        <FieldInput label="Tên danh mục mới" onChange={setNewName} required value={newName} />
        <FieldInput label="Slug danh mục mới" onChange={setNewSlug} required value={newSlug} />
        <FieldInput label="Mô tả danh mục mới" onChange={setNewDescription} required value={newDescription} />
        <FieldInput label="Biểu tượng (không bắt buộc)" onChange={setNewIcon} value={newIcon} />
        <FieldInput label="Thứ tự hiển thị" min="0" onChange={setNewSortOrder} type="number" value={newSortOrder} />
        <label className="flex min-h-11 items-center gap-3 text-sm font-semibold text-[var(--theme-text)]"><input checked={newIsActive} onChange={(event) => setNewIsActive(event.target.checked)} type="checkbox" />Kích hoạt ngay</label>
        <FieldInput label="Lý do tạo danh mục" onChange={setNewReason} required value={newReason} />
        {create.isError ? <p className="text-sm font-semibold text-red-700 sm:col-span-2" role="alert">Chưa thể tạo danh mục. Hãy kiểm tra slug và thử lại.</p> : null}
        <div className="sm:col-span-2"><button className={primaryClass} disabled={!newName.trim() || !newSlug.trim() || !newDescription.trim() || !newReason.trim() || create.isPending} type="submit">Tạo danh mục</button></div>
      </form>
      {notice ? <p aria-live="polite" className="mt-4 text-sm font-semibold text-[var(--theme-accent)]" role="status">{notice}</p> : null}
      {categories.isPending ? <PanelLoading label="Đang tải danh mục" /> : null}
      {categories.isError ? <PanelError message="Chưa thể tải danh mục." onRetry={() => void categories.refetch()} /> : null}
      {categories.data?.length ? <div className="mt-5 space-y-3">
        {categories.data.map((category) => (
          <article className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-5" key={category.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-bold text-[var(--theme-text)]">{category.name}</h3>
                <p className="mt-1 break-words text-sm text-[var(--theme-muted)]">/{category.slug} · {category.isActive ? "Đang hoạt động" : "Đã tạm ngừng"}</p>
                <p className="mt-2 text-sm text-[var(--theme-muted)]">{category.description}</p>
              </div>
              <button className={secondaryClass} onClick={() => startEdit(category)} type="button">Chỉnh sửa danh mục: {category.name}</button>
            </div>
            {editingId === category.id && editDraft ? (
              <form className="mt-4 grid gap-3 border-t border-[var(--theme-border)] pt-4 sm:grid-cols-2" onSubmit={(event) => saveEdit(event, category.id)}>
                <FieldInput label="Tên danh mục" onChange={(value) => setEditDraft((current) => current ? { ...current, name: value } : current)} required value={editDraft.name} />
                <FieldInput label="Slug danh mục" onChange={(value) => setEditDraft((current) => current ? { ...current, slug: value } : current)} required value={editDraft.slug} />
                <FieldInput label="Mô tả danh mục" onChange={(value) => setEditDraft((current) => current ? { ...current, description: value } : current)} required value={editDraft.description} />
                <FieldInput label="Biểu tượng" onChange={(value) => setEditDraft((current) => current ? { ...current, icon: value } : current)} value={editDraft.icon} />
                <FieldInput label="Thứ tự hiển thị" min="0" onChange={(value) => setEditDraft((current) => current ? { ...current, sortOrder: value } : current)} type="number" value={editDraft.sortOrder} />
                <label className="flex min-h-11 items-center gap-3 text-sm font-semibold text-[var(--theme-text)]"><input checked={editDraft.isActive} onChange={(event) => setEditDraft((current) => current ? { ...current, isActive: event.target.checked } : current)} type="checkbox" />Danh mục đang hoạt động</label>
                <FieldInput label="Lý do cập nhật danh mục" onChange={(value) => setEditDraft((current) => current ? { ...current, reason: value } : current)} required value={editDraft.reason} />
                {update.isError ? <p className="text-sm font-semibold text-red-700 sm:col-span-2" role="alert">Chưa thể cập nhật danh mục. Slug có thể đã được sử dụng.</p> : null}
                <div className="flex gap-2 sm:col-span-2"><button className={primaryClass} disabled={!editDraft.name.trim() || !editDraft.slug.trim() || !editDraft.description.trim() || !editDraft.reason.trim() || update.isPending} type="submit">Lưu danh mục</button><button className={secondaryClass} onClick={() => { setEditingId(null); setEditDraft(null); }} type="button">Hủy</button></div>
              </form>
            ) : null}
          </article>
        ))}
      </div> : null}
    </section>
  );
}

interface CategoryDraft {
  name: string;
  slug: string;
  description: string;
  icon: string;
  sortOrder: string;
  isActive: boolean;
  reason: string;
}

export function CommunitySettingsPanel() {
  const queryClient = useQueryClient();
  const settings = useQuery({
    queryKey: ["community", "admin", "settings"],
    queryFn: ({ signal }) => communityAdminApi.settings(signal),
  });
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [reason, setReason] = useState("");
  const [notice, setNotice] = useState("");
  const update = useMutation({
    mutationFn: () => communityAdminApi.updateSettings({
      preModerationEnabled: enabled ?? settings.data?.preModerationEnabled ?? true,
      reason: reason.trim(),
    }),
    onSuccess: async (result) => {
      queryClient.setQueryData<CommunityAdminSettings>(["community", "admin", "settings"], result);
      setEnabled(result.preModerationEnabled);
      setReason("");
      setNotice("Cài đặt đã được lưu.");
      await queryClient.invalidateQueries({ queryKey: ["community", "admin", "moderation-history"] });
    },
  });
  const currentValue = enabled ?? settings.data?.preModerationEnabled ?? false;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reason.trim() || update.isPending) return;
    setNotice("");
    update.mutate();
  }

  return (
    <section aria-labelledby="community-settings-title" className="max-w-3xl">
      <header className="mb-5 border-b border-[var(--theme-border)] pb-4">
        <p className="text-xs font-bold tracking-[0.16em] text-[var(--theme-accent)] uppercase">Quy trình xuất bản</p>
        <h2 className="mt-2 text-2xl font-bold text-[var(--theme-text)]" id="community-settings-title">Cài đặt cộng đồng</h2>
      </header>
      {settings.isPending ? <PanelLoading label="Đang tải cài đặt cộng đồng" /> : null}
      {settings.isError ? <PanelError message="Chưa thể tải cài đặt cộng đồng." onRetry={() => void settings.refetch()} /> : null}
      {settings.data ? <form className="space-y-4 rounded-2xl border border-[var(--theme-border)] bg-[var(--theme-surface)] p-4 sm:p-6" onSubmit={submit}>
        <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-[var(--theme-border)] p-4">
          <input aria-label="Bật duyệt trước khi đăng" checked={currentValue} className="mt-1 size-4 accent-[var(--theme-accent)]" onChange={(event) => setEnabled(event.target.checked)} type="checkbox" />
          <span><span className="block font-bold text-[var(--theme-text)]">Bật duyệt trước khi đăng</span><span className="mt-1 block text-sm leading-6 text-[var(--theme-muted)]">Bài viết gửi lên sẽ chờ người có quyền kiểm duyệt. Khi tắt, bài gửi từ bản nháp được đăng ngay.</span></span>
        </label>
        <FieldTextarea label="Lý do thay đổi" onChange={setReason} required value={reason} />
        <p className="text-xs text-[var(--theme-muted)]">Cập nhật gần nhất: {formatDate(settings.data.updatedAt)}{settings.data.updatedBy ? ` · Tài khoản ${settings.data.updatedBy}` : ""}</p>
        {update.isError ? <p className="text-sm font-semibold text-red-700" role="alert">Không thể lưu cài đặt. Vui lòng thử lại.</p> : null}
        {notice ? <p className="text-sm font-semibold text-[var(--theme-accent)]" role="status">{notice}</p> : null}
        <button className={primaryClass} disabled={!reason.trim() || update.isPending} type="submit">Lưu cài đặt</button>
      </form> : null}
    </section>
  );
}

function FieldInput({ label, onChange, required = false, type = "text", value, min }: {
  label: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: "text" | "number";
  value: string;
  min?: string;
}) {
  const id = `community-field-${slugId(label)}`;
  return <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor={id}>{label}<input className={inputClass} id={id} min={min} onChange={(event) => onChange(event.target.value)} required={required} type={type} value={value} /></label>;
}

function FieldTextarea({ label, onChange, required = false, value }: {
  label: string;
  onChange: (value: string) => void;
  required?: boolean;
  value: string;
}) {
  const id = `community-field-${slugId(label)}`;
  return <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor={id}>{label}<textarea className={textareaClass} id={id} maxLength={2000} onChange={(event) => onChange(event.target.value)} required={required} value={value} /></label>;
}

function FieldSelect({ label, onChange, value, children }: {
  label: string;
  onChange: (value: string) => void;
  value: string;
  children: React.ReactNode;
}) {
  const id = `community-field-${slugId(label)}`;
  return <label className="block text-sm font-semibold text-[var(--theme-text)]" htmlFor={id}>{label}<select className={inputClass} id={id} onChange={(event) => onChange(event.target.value)} value={value}>{children}</select></label>;
}

function PanelLoading({ label }: { label: string }) {
  return <div aria-label={label} className="mt-4 space-y-3" role="status">{[0, 1].map((item) => <div aria-hidden="true" className="h-24 animate-pulse rounded-xl bg-[var(--theme-elevated)]" key={item} />)}</div>;
}

function PanelError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="mt-4 rounded-xl border border-[var(--theme-border)] p-4" role="alert"><p className="text-sm font-semibold text-[var(--theme-text)]">{message}</p><button className={`${secondaryClass} mt-3`} onClick={onRetry} type="button"><RotateCcw aria-hidden="true" className="size-4" /> Thử tải lại</button></div>;
}

function PanelEmpty({ title, body }: { title: string; body: string }) {
  return <div className="mt-4 rounded-xl border border-dashed border-[var(--theme-border)] px-5 py-10 text-center"><h3 className="font-bold text-[var(--theme-text)]">{title}</h3><p className="mt-2 text-sm leading-6 text-[var(--theme-muted)]">{body}</p></div>;
}

function reportReasonLabel(reason: CommunityReportReason): string {
  return {
    SPAM: "Nội dung rác hoặc quảng cáo",
    HARASSMENT: "Quấy rối hoặc công kích",
    HATE_SPEECH: "Ngôn từ thù ghét",
    MISINFORMATION: "Thông tin sai lệch",
    COPYRIGHT: "Vi phạm bản quyền",
    ADVERTISING: "Quảng cáo không phù hợp",
    PRIVACY_VIOLATION: "Xâm phạm quyền riêng tư",
    OTHER: "Lý do khác",
  }[reason];
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function slugId(value: string): string {
  return value.toLocaleLowerCase("vi-VN").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-");
}

const inputClass = "mt-2 min-h-11 w-full rounded-lg border border-[var(--theme-border)] bg-[var(--theme-bg)] p-3 text-sm text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const textareaClass = "mt-2 min-h-24 w-full resize-y rounded-lg border border-[var(--theme-border)] bg-[var(--theme-bg)] p-3 text-sm leading-6 text-[var(--theme-text)] outline-none focus:border-[var(--theme-accent)] focus:ring-2 focus:ring-[var(--theme-accent)]/20";
const primaryClass = "inline-flex min-h-11 items-center justify-center rounded-lg bg-[var(--theme-accent)] px-4 text-sm font-bold text-[var(--theme-accent-contrast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
const secondaryClass = "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[var(--theme-border)] px-4 text-sm font-bold text-[var(--theme-text)] hover:border-[var(--theme-accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] disabled:cursor-not-allowed disabled:opacity-50";
