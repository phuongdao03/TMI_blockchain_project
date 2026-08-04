# Incident response

## Severity and ownership

- **SEV-1:** security exposure, data-integrity risk, public verification down or
  payment corruption. Page incident commander, platform, security and business
  owner immediately.
- **SEV-2:** partial workflow outage, queue delay or material latency
  regression. Page platform owner during support hours and escalate if impact
  grows.
- **SEV-3:** degraded non-critical function with workaround. Create an owned
  ticket.

Never paste tokens, cookies, private keys, raw webhook bodies or personal
documents into chat, tickets or telemetry. Use request IDs and redacted audit
records.

## First 15 minutes

1. Acknowledge the alert and assign incident commander, operations lead and
   communications lead.
2. Record start time, release tag, affected flows and safe request IDs.
3. Check `/health`, `/ready`, error rate, P95 latency, DB pool and queue age.
4. Stop risky writes or disable the affected integration when data integrity is
   uncertain.
5. Rollback the application image when the incident correlates with a release.
6. Preserve logs and audit evidence; do not mutate failed payment or blockchain
   records manually.

## API errors

Compare 5xx endpoints by request ID, check dependency readiness and the latest
release. Roll back above twice baseline or when a new error type is sustained.

## Queue backlog

Check Redis health, worker heartbeat and oldest message age. Restart one worker
only after confirming tasks are idempotent. Scale workers gradually; never purge
the queue as a recovery shortcut.

## Database

Stop deploys, inspect Neon connections and long-running queries. Reduce worker
concurrency before increasing connection limits. Escalate to restore only after
confirming corruption or unrecoverable loss.

## Payment webhook

Verify provider status and signature failures without logging raw payloads.
Reconcile through the service command/API; never mark orders paid directly in
the database.

## Blockchain

Check RPC availability, signer balance, nonce lock and pending transaction age.
Use idempotent reconciliation/retry paths. Never replace a signer key during an
active incident without the key-rotation procedure and dual approval.

## Wallet balance

Confirm the expected network and wallet address, then fund through the approved
treasury process. Treat unexpected balance movement as SEV-1.

## Backup freshness

Run `infrastructure/scripts/check-backup-age.sh <backup-root> 26` on the
isolated operations host. Exit code 70 means the newest bundle is stale; exit
code 65 means no valid bundle was found or validation failed. Open a SEV-2
incident, preserve the last valid bundle, and repair the scheduler before
starting a restore drill. Do not copy secrets into the incident record.

## Resolution

Verify critical user journeys, keep enhanced monitoring for one hour, publish a
sanitized incident summary and schedule a blameless review within two business
days. Track every corrective action with owner and due date.
