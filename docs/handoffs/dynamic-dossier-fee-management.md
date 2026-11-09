# Dynamic dossier fee management handoff

## Delivered

- Added effective-time fee policies scoped to dossier type and fee type. Draft creation and approval are separate; the creator cannot approve their own policy. PostgreSQL advisory locks serialize policy-version creation and approvals for the same scope.
- Added dual-approved, one-use dossier waivers. Amounts are bounded by the current policy, waivers expire, and request/decision/redemption/expiry mutations are audited.
- Submission quote is read-only. Initial submission rechecks the accepted policy version and snapshots the policy, gross fee, waiver, due amount, and obligation. A missing policy or dossier type blocks submission; there is no static 5,000,000 VND fallback or seeded fee.
- Preserved legacy dossier/payment snapshots. Migration `0160_dynamic_dossier_fees` does not backfill rows and refuses unsafe downgrades.
- Added the four-tab admin workspace at `/admin/payments`: Transactions, Waivers, Policies, and Reconciliation. Navigation and actions follow granular permissions; transaction history remains server-paginated.

## APIs and permissions

- `GET/POST /api/v1/admin/fee-policies`; policy `approve` and `cancel` actions.
- `GET/POST /api/v1/admin/fee-waivers`; waiver `approve` and `reject` actions.
- Permissions: `billing.fees.read`, `billing.fees.policies.create|approve|cancel`, `billing.fees.waivers.request|approve`, and existing payment `read|issue|reconcile` capabilities. Migration adds catalog entries only; operators must grant capabilities deliberately.
- `GET /api/v1/dossiers/{id}/submission-fee` includes `feeAvailable`. `X-Fee-Policy-Version` binds initial submission to the displayed version.

## Verification and rollout

- Focused backend policy, waiver, migration, submission, precheck, and payment tests passed (17 cases in the final focused run).
- Selected frontend workspace/navigation suite passed 54 tests. Root format and type checks passed; 501 backend source files pass mypy.
- SQLite migration upgrade/downgrade was exercised against an isolated database. No production database was inspected or changed, and no real payment was attempted.
- Before enabling submissions in an environment, create and approve policies for the dossier types that should accept submissions. Test concurrent PostgreSQL approvals, concurrent submission reservation, and the configured payment-provider sandbox in staging.
