"use client";

import { useState } from "react";
import { UsersRound } from "lucide-react";

import { StaffAccountWorkspace } from "@/components/admin/staff-account-workspace";
import { hrEmployeeApi } from "@/lib/api/client";
import { EmployeeWorkspace } from "./employee-workspace";
import { WorkspacePageHeader } from "@/components/layout/workspace-page-header";

type PeopleView = "accounts" | "employees";
type LinkedAccount = { id: string; email: string };

export function PeopleWorkspace({
  initialAccountSearch = "",
  initialView = "accounts",
}: {
  initialAccountSearch?: string;
  initialView?: PeopleView;
} = {}) {
  const [view, setView] = useState<PeopleView>(initialView);
  const [linkedAccount, setLinkedAccount] = useState<LinkedAccount | null>(
    null,
  );
  const [employeeSearch, setEmployeeSearch] = useState(initialAccountSearch);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [checkingAccount, setCheckingAccount] = useState(false);

  async function openEmployeeProfile(account: LinkedAccount) {
    setCheckingAccount(true);
    setLookupError(null);
    try {
      const response = await hrEmployeeApi.list({
        search: account.email,
        pageSize: 20,
      });
      const existing = response.data.find(
        (employee) =>
          employee.email.toLowerCase() === account.email.toLowerCase(),
      );
      setLinkedAccount(existing ? null : account);
      setEmployeeSearch(existing ? account.email : "");
      setProfileNotice(
        !existing
          ? null
          : existing.userId === account.id
            ? `Hồ sơ của ${account.email} đã liên kết với tài khoản này.`
            : existing.userId
              ? `Email ${account.email} đang thuộc hồ sơ liên kết với tài khoản khác. Kiểm tra hồ sơ trước khi phân công.`
              : `Hồ sơ của ${account.email} chưa liên kết với tài khoản. Chọn Chỉnh sửa trong hồ sơ bên dưới.`,
      );
      setView("employees");
    } catch {
      setLookupError("Không kiểm tra được hồ sơ nhân viên. Vui lòng thử lại.");
    } finally {
      setCheckingAccount(false);
    }
  }

  function showEmployees() {
    setLinkedAccount(null);
    setEmployeeSearch("");
    setProfileNotice(null);
    setView("employees");
  }

  return (
    <div className="people-workspace workspace-screen mx-auto max-w-7xl space-y-6 pb-12">
      <WorkspacePageHeader
        description="Tài khoản để đăng nhập; hồ sơ nhân viên để chấm công và quản lý lao động. Người được mời tự điền thông tin cá nhân, quản trị viên thiết lập công việc."
        icon={UsersRound}
        section="Quản trị nhân sự"
        title="Nhân sự"
      />
      <ol
        aria-label="Quy trình thiết lập nhân viên"
        className="grid gap-0 border-y border-[var(--theme-border)] text-sm sm:grid-cols-3"
      >
        <li className="flex items-start gap-3 py-3 sm:pr-5">
          <span className="font-mono text-xs font-bold text-[var(--theme-accent)]">
            01
          </span>
          <span>Mời hoặc chọn tài khoản đã có</span>
        </li>
        <li className="flex items-start gap-3 border-t border-[var(--theme-border)] py-3 sm:border-t-0 sm:border-l sm:px-5">
          <span className="font-mono text-xs font-bold text-[var(--theme-accent)]">
            02
          </span>
          <span>Thiết lập phòng ban, vị trí và ngày vào làm</span>
        </li>
        <li className="flex items-start gap-3 border-t border-[var(--theme-border)] py-3 sm:border-t-0 sm:border-l sm:pl-5">
          <span className="font-mono text-xs font-bold text-[var(--theme-accent)]">
            03
          </span>
          <span>Gán địa điểm và giờ làm việc</span>
        </li>
      </ol>
      {checkingAccount ? (
        <p className="text-sm text-[var(--theme-muted)]" role="status">
          Đang kiểm tra hồ sơ nhân viên…
        </p>
      ) : null}
      {lookupError ? (
        <p className="text-sm text-rose-700" role="alert">
          {lookupError}
        </p>
      ) : null}
      <nav
        aria-label="Quản lý nhân sự"
        className="flex gap-5 overflow-x-auto border-b border-[var(--theme-border)]"
        role="tablist"
      >
        <button
          aria-controls="people-accounts-panel"
          aria-selected={view === "accounts"}
          className={`min-h-12 shrink-0 border-b-2 px-1 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${view === "accounts" ? "border-[var(--theme-accent)] text-[var(--theme-accent)]" : "border-transparent text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}`}
          id="people-accounts-tab"
          onClick={() => setView("accounts")}
          onKeyDown={(event) => {
            if (event.key !== "ArrowRight") return;
            event.preventDefault();
            showEmployees();
            document.getElementById("people-employees-tab")?.focus();
          }}
          role="tab"
          tabIndex={view === "accounts" ? 0 : -1}
          type="button"
        >
          Tài khoản và quyền
        </button>
        <button
          aria-controls="people-employees-panel"
          aria-selected={view === "employees"}
          className={`min-h-12 shrink-0 border-b-2 px-1 text-sm font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--theme-accent)] ${view === "employees" ? "border-[var(--theme-accent)] text-[var(--theme-accent)]" : "border-transparent text-[var(--theme-muted)] hover:text-[var(--theme-text)]"}`}
          id="people-employees-tab"
          onClick={showEmployees}
          onKeyDown={(event) => {
            if (event.key !== "ArrowLeft") return;
            event.preventDefault();
            setView("accounts");
            document.getElementById("people-accounts-tab")?.focus();
          }}
          role="tab"
          tabIndex={view === "employees" ? 0 : -1}
          type="button"
        >
          Hồ sơ nhân viên
        </button>
      </nav>
      <div
        aria-labelledby="people-accounts-tab"
        hidden={view !== "accounts"}
        id="people-accounts-panel"
        role="tabpanel"
      >
        {view === "accounts" ? (
          <StaffAccountWorkspace
            embedded
            isOpeningEmployee={checkingAccount}
            onCreateEmployee={(account) => void openEmployeeProfile(account)}
          />
        ) : null}
      </div>
      <div
        aria-labelledby="people-employees-tab"
        hidden={view !== "employees"}
        id="people-employees-panel"
        role="tabpanel"
      >
        {view === "employees" && profileNotice ? (
          <p
            className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900"
            role="status"
          >
            {profileNotice}
          </p>
        ) : null}
        {view === "employees" ? (
          <EmployeeWorkspace
            embedded
            initialAccountSearch={employeeSearch}
            initialSearch={employeeSearch}
            linkedAccount={linkedAccount}
            onClearLinkedAccount={() => setLinkedAccount(null)}
          />
        ) : null}
      </div>
    </div>
  );
}
