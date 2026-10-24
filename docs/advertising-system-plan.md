# Advertising System Implementation Plan

## Overview

Build an additive advertising module in risk order. The placement row is the PostgreSQL serialization point for inventory mutations. Wallet payment, order, booking, and ledger debit share one transaction. Existing dossier publication remains unchanged; a campaign references its dossier and delivery checks current public eligibility.

## Architecture Decisions

- Model placements, packages, campaigns, creatives, reservations, bookings, orders, delivery events/stats, waitlist entries, and audit records as separate entities where their lifecycles differ.
- Use half-open UTC intervals and sweep-line checks for capacity; serialize all reservation and capacity edits by locking the placement row.
- Reuse `WalletLedger` for debits and its unique journal reference for idempotency. Do not create a second wallet balance or payment provider.
- Snapshot package price and membership discount on each order. Admin catalog changes affect only new orders.
- Persist delivery selection events in PostgreSQL for cross-worker fairness and measurable metrics; Redis is not the inventory or payment authority.
- Keep public delivery payloads allowlisted and cacheable; never expose owner, wallet, or review data.

## Task List

### Phase 1: Audit and contracts
- [x] Audit existing wallet, payment, membership, dossier, migration, and worker modules.
- [x] Record the feature contract and phased implementation boundaries.
- [x] Add API schemas, domain states, and migration/model registration.

### Phase 2: Inventory and reservation
- [x] Seed the four configurable placements and default featured package.
- [x] Implement interval capacity, availability suggestions, waitlists, and reservation lifecycle.
- [ ] Prove simultaneous final-slot holds are serialized on PostgreSQL (test is present; needs a disposable PostgreSQL URL).

### Phase 3: Checkout
- [x] Add campaign/creative review, quote snapshots, membership allowance accounting, and idempotent wallet checkout.
- [x] Commit order, wallet journal, reservation, and booking atomically.

### Phase 4: Advertiser UI
- [ ] Add mobile-first package, schedule, checkout, and campaign views (gated on PostgreSQL race proof).
- [ ] Handle insufficient balance and expired reservation by rechecking capacity and requiring confirmation.

### Phase 5: Delivery
- [x] Add persistent weighted fair shared-placement selection, exclusive placement handling, impression/click events, and campaign start/end workers.
- [x] Restrict delivery to paid, approved, scheduled campaigns with publicly eligible dossiers.

### Phase 6: Dossier integration
- [x] Allow pre-publication and post-publication campaign creation without changing or gating dossier publication.
- [ ] Add advertiser UI entry points from dossier pages (gated on PostgreSQL race proof).

### Phase 7: Admin
- [x] Add placement/package configuration APIs, inventory calendar data, creative moderation, campaign pause, and reports.
- [x] Prevent capacity reductions that conflict with confirmed commitments.
- [ ] Add admin inventory and moderation screens (gated on PostgreSQL race proof).

### Phase 8: Verification and handoff
- [x] Run focused backend tests, lint, type checking, OpenAPI generation, and SQLite migration upgrade/downgrade checks.
- [ ] Run PostgreSQL concurrency and mobile/browser verification.
- [x] Document API/state transitions, algorithms, admin setup, and remaining operational risks.

## Current Gate

Backend inventory, checkout, delivery, moderation, metrics, and admin APIs are implemented. The PostgreSQL concurrency test is skipped unless `ADVERTISING_TEST_DATABASE_URL` points to a disposable PostgreSQL database. Advertiser and admin UI work remains gated until that test passes; no production deployment has been performed.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Concurrent reservations oversell | Critical | Lock placement row before checking and inserting; PostgreSQL concurrency integration test. |
| Wallet debit without booking | Critical | One database transaction for ledger, order, booking, and reservation confirmation. |
| Existing uncommitted wallet/payment changes | High | Keep changes additive; avoid rewriting shared payment modules unless required. |
| Dossier publication states vary | High | Delivery checks current public visibility/status at selection time; publication workflow stays independent. |
| Missing package prices | Medium | Seed only the explicitly priced package; admin creates the rest. |
| Lowering capacity breaks a sold commitment | High | Validate the maximum overlap across all confirmed intervals before applying an effective configuration. |

## Verification Checkpoints

- Inventory checkpoint: sweep-line unit cases pass; PostgreSQL race test yields exactly one final-slot reservation.
- Checkout checkpoint: insufficient funds and repeated payment requests never create duplicate debit or booking.
- Delivery checkpoint: no unpaid, unapproved, expired, paused, or non-public dossier campaign is served.
- Release checkpoint: migrations upgrade/downgrade cleanly; UI works at 360px–1440px; no production deployment is performed.
