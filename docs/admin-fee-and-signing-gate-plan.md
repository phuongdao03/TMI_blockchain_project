# Implementation plan: Admin fee decision and signing gate

## Phase 1: State and API safety

- [ ] Add regression tests proving unpaid dossiers cannot enter the signer queue
      or create an intent.
- [ ] Add a tested, idempotent free/waiver endpoint that transitions an approved
      dossier to the existing paid-ready state and notifies both parties.
- [ ] Notify admins after provider-verified or manually confirmed payment.

Checkpoint: focused payment and proof-registry backend tests pass.

## Phase 2: Admin fee workspace

- [ ] Load approved dossiers and replace the UUID text field with an accessible
      dossier selector.
- [ ] Add paid/free choice with mode-specific validation, feedback, and safe
      retry behavior.
- [ ] Add API types/client for the waiver response.

Checkpoint: component tests cover paid, free, loading, success, and errors.

## Phase 3: Signing reliability and presentation

- [ ] Prove EIP-1193 quantities are hexadecimal, then fix the intent contract.
- [ ] Improve signing-stage errors and show the full verified signer/contract
      distinction with copy actions.
- [ ] Refine responsive layout, hierarchy, loading, empty, and success states
      within the existing theme tokens.

Checkpoint: signing component/API tests and browser-relevant tests pass.

## Phase 4: Verification

- [ ] Run focused tests after each slice.
- [ ] Run format, typecheck, lint, full relevant suites, and production build.
- [ ] Review diff and exclude existing user media and unrelated auth work from
      any future commit.

## Risks

- Duplicate fee clicks: preserve idempotency keys and status transition guards.
- Duplicate notifications: use per-user/source-event uniqueness and exclude the
  applicant from the admin recipient set.
- Incorrect signer: require the active verified wallet, app permission, chain,
  and on-chain role on every intent.
- Provider delay: only webhook/reconciliation/manual evidence marks a paid
  order.
