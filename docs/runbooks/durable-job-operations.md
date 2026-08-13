# Durable job operations

## Purpose

Use the internal operations dashboard to inspect and recover failed blockchain
and payment reconciliation work. Never edit a stored job intent or publish an
ad-hoc Celery payload.

## Access

- `FINANCE_ADMIN` and `BLOCKCHAIN_ADMIN` may view aggregate operations metrics.
- Only `SUPER_ADMIN` with `operations.jobs.manage` may replay or cancel jobs.
- Every replay/cancellation requires a reason and creates a sealed audit event.

## Triage

1. Open **Quản trị → Tổng quan vận hành → Công việc nền gần đây**.
2. Check the user-facing status, attempt count and last update time.
3. Expand **Xem chi tiết** only when a technical identifier is needed for logs.
4. Correlate using the job ID/correlation ID; never copy credentials or provider
   payloads into notes.
5. Resolve the upstream incident before replaying an exhausted job.

## Safe replay

Replay is allowed only for the server-owned immutable intents below:

- blockchain broadcast;
- blockchain confirmation;
- blockchain reconciliation;
- pending payment reconciliation.

The API rejects payload changes, unsupported task names, stale versions and
concurrent operator actions. A replay creates a fresh delivery identity while
retaining the original durable job and idempotency boundary.

## Cancellation

Only queued or exhausted jobs can be cancelled. Running and completed jobs are
not cancellable. Cancellation preserves attempts and audit history.

## Failure during broker publication

If broker publication fails after the database commit, the job remains `QUEUED`
with no new attempt. Do not insert queue messages manually. Restore the broker,
verify queue health, then use the controlled operations workflow.

## Alert thresholds

Configure the monitoring platform to poll the protected operations metrics and
alert on:

- **SEV-2:** `durable_job_dead_lettered_count > 0` for payment or blockchain
  tasks for 5 minutes;
- **SEV-2:** `durable_job_oldest_queued_seconds > 600` for 5 minutes;
- **SEV-3:** `durable_job_retry_failure_count` increases continuously for 15
  minutes;
- **SEV-3:** queue depth grows for 15 minutes without successful completions.

Escalate using [incident-response.md](incident-response.md). For chain-specific
failures, also follow [blockchain-release.md](blockchain-release.md); for real
payments, follow [payos-merchant-readiness.md](payos-merchant-readiness.md).

## Verification after recovery

1. Confirm the job reaches `SUCCEEDED` and no duplicate side effect exists.
2. Confirm blockchain transaction/payment reconciliation state matches the
   authoritative provider.
3. Confirm the replay audit record contains actor, reason and version change.
4. Watch queue age and dead-letter count for at least 15 minutes.
