# Voucher administration

Open `/admin/promotions` with `SUPER_ADMIN` or the appropriate promotion permission.

1. Create a draft in **Chiến dịch**. Complete information, discount, service,
   audience, validity, limits, presentation and review steps.
2. Upload a PNG/JPEG/WebP with meaningful alternative text. Select desktop/mobile,
   card or thumbnail placement; configure fit and focal point. Check both previews.
3. For the early-member campaign, set the actual approved registration cutoff.
   Review expiry, recipient conditions, start time and budget.
4. Save, then publish through the confirmation dialog. A future start is scheduled.
5. In **Phân phối**, select the campaign. Use its audience rules or select account
   IDs through email/ID search or CSV. Preview exclusions and eligible totals.
6. Enter a reason and confirm distribution. Follow persisted job progress and
   inspect failures. Repeating the same request does not duplicate grants.
7. Use reports and audit to inspect actual usage, commitments and net discounts.
   CSV export includes all matching transactions, beyond the first display page.

Customers cannot convert a voucher to wallet funds or withdraw it. Pausing issuance
does not rewrite rights already captured in a claim; its snapshot controls use.
Copy an issued campaign when changing economic conditions.

Before production: review migrations/backups, assign permissions, run workers and
Redis, configure the approved 200K campaign, validate provider reconciliation and
complete the remaining environment checks in the test plan. No production deploy
or real-money test is part of this implementation session.
