"use client";

import { useEffect, useState } from "react";

import { StaffAccountWorkspace } from "@/components/admin/staff-account-workspace";
import { hrEmployeeApi } from "@/lib/api/client";
import { EmployeeWorkspace } from "./employee-workspace";

type PeopleView = "accounts" | "employees";
type LinkedAccount = { id: string; email: string };

export function PeopleWorkspace() {
  const [view, setView] = useState<PeopleView>("accounts");
  const [linkedAccount, setLinkedAccount] = useState<LinkedAccount | null>(
    null,
  );
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [profileNotice, setProfileNotice] = useState<string | null>(null);
  const [checkingAccount, setCheckingAccount] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("view") !== "employees") return;
    const account = params.get("account")?.trim() ?? "";
    setEmployeeSearch(account);
    setView("employees");
  }, []);

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
    <div className="people-workspace mx-auto max-w-7xl space-y-6 pb-12">
      <header className="border-b border-neutral-200 pb-5">
        <h1 className="text-2xl font-bold text-neutral-950">Nhân sự</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
          Tài khoản dùng để đăng nhập và nhận quyền. Hồ sơ nhân viên dùng cho
          chấm công, nghỉ phép và thông tin lao động.
        </p>
        <ol className="mt-4 grid gap-2 text-sm sm:grid-cols-3">
          <li className="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <strong className="text-primary-700">01</strong> Mời tài khoản và
            chờ người dùng chấp nhận
          </li>
          <li className="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <strong className="text-primary-700">02</strong> Tạo hồ sơ nhân
            viên, liên kết tài khoản
          </li>
          <li className="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <strong className="text-primary-700">03</strong> Phân công địa điểm
            chấm công
          </li>
        </ol>
        {checkingAccount ? (
          <p className="mt-3 text-sm text-neutral-600" role="status">
            Đang kiểm tra hồ sơ nhân viên…
          </p>
        ) : null}
        {lookupError ? (
          <p className="mt-3 text-sm text-rose-700" role="alert">
            {lookupError}
          </p>
        ) : null}
        <div
          aria-label="Quản lý nhân sự"
          className="mt-5 flex flex-wrap gap-2"
          role="tablist"
        >
          <button
            aria-controls="people-accounts-panel"
            aria-selected={view === "accounts"}
            className={`min-h-11 rounded-xl px-4 text-sm font-bold ${view === "accounts" ? "bg-primary-700 text-white" : "border border-neutral-300 text-neutral-700 hover:bg-neutral-50"}`}
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
            className={`min-h-11 rounded-xl px-4 text-sm font-bold ${view === "employees" ? "bg-primary-700 text-white" : "border border-neutral-300 text-neutral-700 hover:bg-neutral-50"}`}
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
        </div>
      </header>
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
