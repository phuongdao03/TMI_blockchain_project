# Dynamic dossier fee rollout

## Current behavior

- New dossiers use dynamic fee policies. A policy must be approved by a different administrator and effective at the server's current UTC time.
- The quote endpoint is read-only. Submission rechecks the policy version and requires the applicant's consent before creating one immutable fee obligation and wallet payment order.
- If no approved policy exists for the dossier type, the quote is unavailable and submission remains blocked. No default amount is inferred from repository configuration.
- Existing dossiers, fee obligations, payment orders, and paid history retain their legacy mode and recorded values. No backfill is performed.
- Approved waivers require a distinct approver and are redeemed once against the matching dossier and fee type.

## Migration and deployment

Migration `0160_dynamic_dossier_fees` adds policy, policy-event, waiver, and obligation snapshot storage. It inserts permission catalog entries but does not assign them to roles or create a fee policy. Apply it only through the normal reviewed deployment process; this task did not connect to or migrate a production database.

Deploy the API, workers, and frontend together after the migration. Before accepting new submissions in a target environment, grant the required capabilities and create and approve policies for each dossier type that should accept submissions. Verify each effective amount and interval in that environment. Until a policy is active, new submissions of that type fail closed.

## Compatibility and rollback

Do not rewrite historical prices or payment records. Downgrade refuses once policies, waivers, policy-backed obligations, dynamic dossiers, or incompatible obligation rows exist. After those records exist, roll forward; do not downgrade the schema or run an older application against dynamic-fee submissions.

## Verification performed in this task

- Isolated SQLite migration upgrade/downgrade and focused fee/submission tests passed; no production migration or live payment was run.
- The selected frontend regression suite passed 54 tests. Root format and type checks passed.
- PostgreSQL concurrency and payment-provider sandbox behavior still require staging verification.
