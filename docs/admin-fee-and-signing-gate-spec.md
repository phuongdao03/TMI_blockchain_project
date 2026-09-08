# Spec: Admin fee decision and blockchain signing gate

## Objective

Make the post-review lifecycle explicit and safe:

`APPROVED -> admin fee decision -> PAYMENT_PENDING -> verified payment -> PAID -> blockchain signing`

or, for a free dossier:

`APPROVED -> admin marks free -> PAID -> blockchain signing`

The applicant receives the fee/free notification. Admins receive a notification
when payment is verified (or the dossier is marked free), and only then can the
designated organization signer record the proof on Polygon.

## Assumptions

1. A free decision is an audited fee waiver and advances the existing dossier to
   `PAID`; no zero-value PayOS order is created.
2. A paid decision keeps the existing PayOS order contract and allowed VND
   range.
3. The active verified wallet link is the signer source of truth. The signer
   must also own `blockchain.sign` and the on-chain `ISSUER_ROLE`.
4. The registry contract address is not a signer wallet.

## Contract

- Keep `POST /api/v1/admin/dossiers/{dossierId}/payment-orders` for paid fees.
- Add `POST /api/v1/admin/dossiers/{dossierId}/payment-waiver` with a required
  reason and `Idempotency-Key`.
- A waiver returns dossier ID/status and whether blockchain signing is ready.
- Paid and free decisions create applicant notifications and audit evidence.
- Verified payment and free decisions create notifications for active Super
  Admin accounts linking to `/blockchain`.
- The proof-registry queue and intent endpoint accept only `PAID` or later
  states, never `APPROVED` or `PAYMENT_PENDING`.
- EIP-1193 transaction quantities use `0x`-prefixed hexadecimal values.

## User experience

- Admin selects an approved dossier by code/title instead of typing its UUID.
- Admin explicitly chooses `Có thu phí` or `Miễn phí` before submitting.
- Paid mode shows amount, description and optional due date; free mode requires
  a waiver reason and does not call PayOS.
- Success, loading, invalid, and provider-error states remain inline and
  preserve entered data.
- The signing workspace clearly distinguishes verified signer, connected wallet,
  Polygon network, registry contract, gas currency (`POL`), and signing stages.
- Errors identify the failed stage and preserve the selected dossier for retry.

## Commands

- Backend tests: `python -m pytest backend/app/tests -q`
- Frontend tests: `npm --prefix frontend test -- --run`
- Format: `npm run format:check`
- Typecheck: `npm --prefix frontend run typecheck`
- Lint: `npm --prefix frontend run lint`
- Build: `npm --prefix frontend run build`

## Boundaries

- Always: validate server-side, keep operations idempotent, notify without
  exposing secrets, and preserve existing paid-order compatibility.
- Ask first: contract deployment, role grants, wallet rotation, or production
  transaction broadcast.
- Never: store private keys/seed phrases or treat a browser return as payment
  confirmation.

## Success criteria

- Entering a dossier code is no longer required; the admin chooses an approved
  dossier from server data.
- Free dossiers reach signing without a PayOS order and leave workflow/audit
  evidence.
- Paid dossiers do not appear in the signing queue until payment is verified.
- Admin receives a payment-ready-for-signing notification.
- MetaMask receives valid hexadecimal transaction quantities.
- UI works in light/dark mode and at mobile/desktop widths.
- Focused backend/frontend tests, typecheck, lint, formatting, and production
  build pass.
