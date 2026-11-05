# Wallet Withdrawal and Affiliate Specification

## Objective

Extend the existing Tinh Hoa Việt prepaid service wallet with a separately
accounted affiliate commission balance, bank account management, manually
approved withdrawals, and referral attribution/commission workflows. Keep all
financial decisions on the backend and preserve existing dossier, membership,
advertising, and payment behavior.

## Verified stack

- Backend: Python 3.12, FastAPI, async SQLAlchemy 2, Alembic, PostgreSQL;
  SQLite is used by domain tests. Celery and Redis are present.
- Frontend: Next.js App Router 16, React 19, TypeScript, TanStack Query,
  Tailwind CSS 4, Vitest/RTL, and Playwright.
- Existing wallet/payOS collection and bank-account/withdrawal review flows are
  implemented. A separately gated payOS payout adapter and worker are wired;
  live payouts remain disabled by default. Affiliate backend APIs and
  commission processing remain pending. The affiliate UI shell is not integrated
  because its backend endpoints are absent.

## User-visible scope

- User wallet summary separates prepaid service balance, pending/available
  commission, reserved withdrawal, and withdrawn totals.
- Users manage bank accounts and can request/cancel a withdrawal while it is
  still awaiting review. A request is reserved atomically and starts at
  `PENDING_REVIEW`.
- Every payout requires a human finance approval and a separate
  `finance.payouts.execute` dispatch. Rejection releases the reservation once.
  The payout worker uses a stable provider reference/idempotency key and polls
  known payOS payout IDs; ambiguous outcomes retain the reserve. Live execution
  remains disabled until legal, provider, and operations gates are satisfied.
- Eligible ordinary USER accounts receive a stable referral profile/code
  automatically. Admin, moderator/reviewer, and other privileged accounts are
  excluded, including mixed-role accounts.
- Referral tracking and service commissions must use server-owned attribution,
  versioned rules, a holding state, and mandatory human approval before credit;
  these backend flows remain pending.
- Admin screens provide withdrawal and commission review, configuration, and
  audit history under backend-enforced finance permissions.

## Financial invariants

- VND amounts are positive integer minor units; no floating-point money math.
- Existing `wallets.balance_minor` remains a service-spending balance and is
  never withdrawable.
- New append-only, balanced finance journals account for commission available,
  reserved, expenses, and payout settlement. A journal source and idempotency
  key may post once.
- A withdrawal is reserved with its `PENDING_REVIEW` row in one transaction.
  There is no provider call before approval and separate authorized dispatch.
  Unknown provider outcomes keep the funds reserved and require reconciliation.
- Admin approval/rejection, commission decisions, and balance changes are
  audited; commission credit requires a unique commission source.
- Auto-approval, level-two commission, and live payouts default off.

## Bổ sung: lệnh nạp ví và giao diện cộng đồng

- Lệnh nạp ví hết hạn sau 10 phút kể từ lúc tạo; thời hạn được gửi cho payOS
  và lệnh đang chờ cũ được rút ngắn để tác vụ đối soát đóng lệnh quá hạn.
- Thanh toán đã được nhà cung cấp xác nhận vẫn được ghi có đúng một lần, kể cả
  khi xác nhận đến muộn sau hạn.
- Số tiền nạp tối thiểu là 5.000 đồng, không áp trần nghiệp vụ 1 tỷ đồng. Giao
  diện hiển thị dấu chấm phân cách hàng nghìn nhưng gửi số nguyên lên API.
- Luồng bài viết cộng đồng trên điện thoại dùng thẻ dễ quét, ảnh xem trước có
  chiều cao giới hạn và mở ảnh đầy đủ khi người dùng chọn; bộ chọn kích thước
  ảnh không xuất hiện trong danh sách bài viết.

## Project structure and commands

- Backend modules: `backend/app/modules/wallet` and focused FastAPI routes in
  `backend/app/api/v1`; the affiliate backend module/API is still pending.
- Frontend: existing wallet/withdrawal components plus an affiliate UI shell
  under `frontend/src/components/affiliate`; affiliate API integration and
  admin commission review remain pending.
- Migrations: `backend/alembic/versions`; focused tests in
  `backend/app/tests` and colocated frontend `*.test.tsx` files.
- Verify: `python -m pytest backend/app/tests -q`; `npm --prefix frontend run
  test`; `npm run typecheck`; `npm run lint`; `npm --prefix frontend run build`.

## Conventions

Use async service functions and the caller's SQLAlchemy transaction; keep
router validation and response schemas explicit. Use `AuthorizationPolicy`,
owner-scoped reads, existing notifications/audit records, and TanStack Query
patterns. Money is represented by integer `amount_minor`/`*_minor` fields.

## Boundaries and open release gates

- Always use idempotency, unique constraints, row locks, append-only journal
  records, and provider reconciliation before releasing reserved money.
- Database schema and API additions are explicitly authorized by the supplied
  implementation request.
- Never withdraw prepaid service funds, auto-approve commissions or
  withdrawals, retry an uncertain payout create, or use real bank transfers in
  tests.
- The repository has no verified KYC/tax eligibility workflow or bank BIN
  catalogue. Live withdrawals must remain unavailable until those are supplied
  and approved. Commission rates in the prompt are examples, not approved
  policies; no rate may be enabled implicitly.
- Production activation requires a verified payOS payout account and
  credentials, supported bank catalogue, legal/compliance decision, terms,
  operational reconciliation, and deployment sign-off.

## Success criteria

1. Existing wallet topups and service payments keep their current behavior.
2. Commission funds cannot be confused with or spent from the prepaid wallet.
3. User withdrawals are owner-scoped, idempotent, atomically reserved, and
   always manually approved before payout.
4. Commission requires eligible paid service, immutable rule snapshot,
   hold-period completion, and admin approval before becoming available.
5. Admin/reviewer roles cannot earn commissions or self-approve financial
   actions without the required backend capability.
6. Migrations are reversible only when no protected financial history exists;
   test suites cover critical invariants and no test contacts a bank.

## Giao diện tiếng Việt và tiêu chuẩn hoàn thiện

- Tất cả nội dung người dùng nhìn thấy trong các màn Ví và Tiếp thị liên kết
  đều dùng tiếng Việt, bao gồm nhãn, trạng thái, nút thao tác, nội dung trợ
  giúp, trạng thái tải, lỗi và dữ liệu rỗng. Mã trạng thái và mã dịch vụ chỉ
  dùng nội bộ cho API; giao diện hiển thị tên tiếng Việt tương ứng.
- Các màn `/wallet`, `/affiliate`, `/admin/withdrawals` và
  `/admin/affiliate` dùng cùng hệ thống màu, kiểu chữ và nhịp khoảng cách của
  Tinh Hoa Việt; biểu mẫu, danh sách và trạng thái phản hồi dễ quét trên màn
  hình nhỏ và lớn.
- Tác vụ tài chính, quyền hạn, quy tắc kiểm duyệt và hợp đồng API giữ nguyên.
