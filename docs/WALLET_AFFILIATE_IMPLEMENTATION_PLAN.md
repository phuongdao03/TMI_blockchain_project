# Wallet and Affiliate Implementation Plan

This plan follows `WALLET_AFFILIATE_ARCHITECTURE.md` and
`WALLET_AFFILIATE_SPEC.md`. Implement in dependency order and keep release gates
closed until verification is complete.

## Current implementation checkpoint

- Audit, finance ledger, bank-account storage, withdrawal reservation/review,
  payOS payout adapter/worker, and wallet/admin withdrawal UI are present in the
  current working tree. Payout and withdrawal gates remain closed by default.
- Affiliate backend/API, commission lifecycle integration, admin commission
  review, and integrated affiliate UI data flow remain pending. The affiliate
  page is a UI shell with client calls whose backend endpoints are absent.
- Final test execution for payout changes is pending; see
  `WALLET_AFFILIATE_TEST_REPORT.md`.

## Giao diện tiếng Việt và hoàn thiện trải nghiệm

1. **Chuẩn hóa ngôn ngữ** — rà soát màn Ví, rút tiền và tiếp thị liên kết;
   Việt hóa toàn bộ nội dung hiển thị, ánh xạ mã trạng thái/dịch vụ sang nhãn
   tiếng Việt và giữ nguyên giá trị gửi lên API.
2. **Hoàn thiện màn quản trị** — nhóm hồ sơ, duyệt hoa hồng, quy tắc và điều
   hành tài chính thành các vùng rõ ràng; chuẩn hóa bộ lọc, nhãn, nút, lỗi,
   trạng thái rỗng và phản hồi thao tác.
3. **Hoàn thiện màn người dùng** — làm rõ số dư có thể rút, tài khoản nhận,
   điều kiện, lịch sử và trạng thái; giữ bố cục thích ứng.
4. **Rà soát trình duyệt** — mở lại bốn tuyến trên ở màn hình rộng và hẹp;
   kiểm tra nội dung hiển thị, nhãn truy cập và bố cục. Không xác nhận dữ liệu
   thật nếu API hoặc phiên xác thực mock chưa sẵn sàng.

## Remaining work

1. **Affiliate foundation** — implement eligible profile/code creation,
   idempotent existing-user backfill, role-change suspension, referral click,
   attribution policy, and privacy limits.
2. **Commissions** — implement versioned configurable rules, eligible paid
   service source events, hold/review states, manual approval, finance-ledger
   credit, rejection, and refund reversals.
3. **Affiliate API and UI integration** — add owner-scoped profile/referral/
   commission APIs and admin review/configuration routes. Connect existing
   affiliate UI shells only after those contracts are live; add backend-backed
   loading, empty, error, and permission states.
4. **Payout hardening** — add focused adapter/worker/API tests, examine unknown
   outcomes without a provider ID, and provide operators a safe resolution path.
   The current adapter creates and queries by payout ID; it does not provide
   list, estimate-credit, or payout-balance operations.
5. **Release readiness** — complete security and concurrency review, migration
   checks, legal/provider approvals, monitoring, reconciliation, deployment,
   rollback, and the test report. Keep live payout disabled until approved.

## Existing financial implementation

The prepaid `Wallet.balance_minor` remains separate from commission accounts.
Finance entries are integer VND, balanced pairs with idempotency/source keys
and immutability triggers. Withdrawal requests reserve commission atomically
and start at `PENDING_REVIEW`. A permission-gated operator approval is followed
by a separate `finance.payouts.execute` dispatch. The payout worker uses the
separate payOS payout credentials/signature and polls known payout IDs. Unknown
outcomes retain the reserve; if no payout ID is known, manual provider
resolution is required. Defaults remain disabled.

## Verification per slice

- Backend: focused pytest files, then the full backend suite.
- Frontend: focused Vitest files, typecheck, lint, build, and mobile E2E with
  mock adapters.
- Database: isolated migration/model checks; never use a production database
  for rollback verification.
- Review each diff for effects on existing payment, membership, advertising,
  and dossier behavior.

## Wallet and community refinement

1. **Top-up expiry and validation** — use a 10-minute wallet-only provider TTL,
   expire/cancel pending orders during reconciliation, shorten active pending
   order timestamps, and retain late verified payment settlement.
2. **Amount entry** — enforce the 5,000 VND minimum at API/service boundaries,
   remove the 1 billion VND cap, and format display digits with Vietnamese
   thousands separators while sending an integer amount.
3. **Community feed** — present posts as readable responsive cards, constrain
   feed image previews, and keep full-size image viewing in the image dialog.
4. **Checkpoint** — inspect the feed and wallet at mobile/desktop widths; run
   typecheck, targeted lint, and whitespace checks. Automated tests were not
   requested for this change.

## External activation gates

- payOS payout account, credentials, eligibility, supported destination banks,
  fees, and limits are confirmed by the account owner/provider.
- Legal, tax, privacy, identity, and affiliate terms are approved.
- Finance permissions are assigned to named operators; dual approval and
  reconciliation are exercised.
- Unknown payout outcomes, incident recovery, alerts, backups, and rollback are
  rehearsed.
